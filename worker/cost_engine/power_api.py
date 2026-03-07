from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from typing import Protocol

import websockets
from fastapi import APIRouter, WebSocket

from worker.cost_engine.PwrEngine.PwrLnx import PwrLnx
from worker.cost_engine.PwrEngine.PwrMac import PwrMac
from worker.cost_engine.PwrEngine.PwrWin import PwrWin

logger = logging.getLogger(__name__)


class PowerMeterProtocol(Protocol):
    async def get_power_watts(self) -> float:
        ...


@dataclass(slots=True)
class PowerSample:
    unix_ms: int
    monotonic_ms: int
    cpu_watts: float
    gpu_watts: float
    total_watts: float
    source: str


@dataclass(slots=True)
class TaskPowerReport:
    elapsed_sec: float
    avg_power_watts: float
    sampled_energy_ws: float


class PlatformPowerReader:
    def __init__(self, fallback_watts: float, win_url: str = "http://127.0.0.1:8085") -> None:
        self.fallback_watts = float(fallback_watts)
        self._impl = self._build_reader(win_url=win_url)

    @staticmethod
    def _build_reader(win_url: str):
        if sys.platform.startswith("win"):
            return PwrWin(base_url=win_url)
        if sys.platform == "darwin":
            return PwrMac()
        return PwrLnx()

    def read(self) -> PowerSample:
        now_unix_ms = int(time.time() * 1000)
        now_mono_ms = int(time.monotonic() * 1000)
        try:
            reading = self._impl.read()
            total = float(reading.total_watts)
            if total <= 0:
                total = self.fallback_watts
            return PowerSample(
                unix_ms=now_unix_ms,
                monotonic_ms=now_mono_ms,
                cpu_watts=float(reading.cpu_watts),
                gpu_watts=float(reading.gpu_watts),
                total_watts=float(total),
                source=str(reading.source),
            )
        except Exception as exc:
            logger.warning("Power read failed, use fallback %.2fW: %s", self.fallback_watts, exc)
            return PowerSample(
                unix_ms=now_unix_ms,
                monotonic_ms=now_mono_ms,
                cpu_watts=0.0,
                gpu_watts=0.0,
                total_watts=self.fallback_watts,
                source="fallback",
            )


class LocalPowerApi:
    def __init__(self, reader: PlatformPowerReader, interval_sec: float = 1.0) -> None:
        self.reader = reader
        self.interval_sec = max(0.2, float(interval_sec))
        self._latest: PowerSample | None = None
        self._task: asyncio.Task | None = None
        self._queues: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="local-power-sampler")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    def get_latest(self) -> PowerSample | None:
        return self._latest

    async def _loop(self) -> None:
        while True:
            started = time.monotonic()
            sample = await asyncio.to_thread(self.reader.read)
            self._latest = sample
            payload = json.dumps({"type": "power_sample", **asdict(sample)}, ensure_ascii=False)
            async with self._lock:
                stale: list[asyncio.Queue[str]] = []
                for queue in self._queues:
                    try:
                        queue.put_nowait(payload)
                    except asyncio.QueueFull:
                        with contextlib.suppress(asyncio.QueueEmpty):
                            queue.get_nowait()
                        with contextlib.suppress(asyncio.QueueFull):
                            queue.put_nowait(payload)
                    except Exception:
                        stale.append(queue)
                for queue in stale:
                    self._queues.discard(queue)
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.0, self.interval_sec - elapsed))

    async def _subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=5)
        async with self._lock:
            self._queues.add(queue)
        latest = self._latest
        if latest:
            payload = json.dumps({"type": "power_sample", **asdict(latest)}, ensure_ascii=False)
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)
        return queue

    async def _unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._queues.discard(queue)

    async def serve_websocket(self, ws: WebSocket) -> None:
        await ws.accept()
        queue = await self._subscribe()
        try:
            while True:
                data = await queue.get()
                await ws.send_text(data)
        except Exception:
            return
        finally:
            await self._unsubscribe(queue)


class LocalPowerMeter(PowerMeterProtocol):
    def __init__(self, api: LocalPowerApi, fallback_watts: float) -> None:
        self.api = api
        self.fallback_watts = float(fallback_watts)

    async def get_power_watts(self) -> float:
        latest = self.api.get_latest()
        if latest:
            return float(latest.total_watts)
        return self.fallback_watts


class ActiveTaskRegistry:
    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = asyncio.Lock()

    async def start(self, job_id: str) -> None:
        async with self._lock:
            self._active.add(job_id)

    async def stop(self, job_id: str) -> None:
        async with self._lock:
            self._active.discard(job_id)

    async def count(self) -> int:
        async with self._lock:
            return max(1, len(self._active))


class PowerWebsocketClient:
    def __init__(self, ws_url: str, timeout_sec: float = 5.0) -> None:
        self.ws_url = ws_url
        self.timeout_sec = float(timeout_sec)
        self._ws = None

    async def __aenter__(self):
        self._ws = await websockets.connect(self.ws_url, open_timeout=self.timeout_sec, close_timeout=2)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def recv_sample(self) -> PowerSample:
        if not self._ws:
            raise RuntimeError("websocket not connected")
        raw = await self._ws.recv()
        data = json.loads(raw)
        return PowerSample(
            unix_ms=int(data.get("unix_ms") or 0),
            monotonic_ms=int(data.get("monotonic_ms") or 0),
            cpu_watts=float(data.get("cpu_watts") or 0.0),
            gpu_watts=float(data.get("gpu_watts") or 0.0),
            total_watts=float(data.get("total_watts") or 0.0),
            source=str(data.get("source") or "unknown"),
        )


class TaskPowerAttributor:
    def __init__(self, ws_url: str, registry: ActiveTaskRegistry, fallback_watts: float) -> None:
        self.ws_url = ws_url
        self.registry = registry
        self.fallback_watts = float(fallback_watts)

    async def track(self, job_id: str, stop_event: asyncio.Event) -> TaskPowerReport:
        await self.registry.start(job_id)
        started = time.monotonic()
        prev_ts = started
        prev_watts = self.fallback_watts
        weighted_watts_sec = 0.0
        total_elapsed = 0.0
        try:
            async with PowerWebsocketClient(self.ws_url) as client:
                while not stop_event.is_set():
                    try:
                        sample = await asyncio.wait_for(client.recv_sample(), timeout=2.5)
                    except asyncio.TimeoutError:
                        now = time.monotonic()
                        seg = max(0.0, now - prev_ts)
                        active = await self.registry.count()
                        weighted_watts_sec += seg * (prev_watts / active)
                        total_elapsed += seg
                        prev_ts = now
                        continue

                    now_mono = float(sample.monotonic_ms) / 1000.0
                    if now_mono <= 0:
                        now_mono = time.monotonic()
                    seg = max(0.0, now_mono - prev_ts)
                    active = await self.registry.count()
                    weighted_watts_sec += seg * (prev_watts / active)
                    total_elapsed += seg
                    prev_ts = now_mono
                    prev_watts = max(0.0, float(sample.total_watts))
        except Exception as exc:
            logger.warning("Power websocket tracking failed for job=%s: %s", job_id, exc)
        finally:
            ended = time.monotonic()
            seg = max(0.0, ended - prev_ts)
            active = await self.registry.count()
            weighted_watts_sec += seg * (prev_watts / active)
            total_elapsed += seg
            await self.registry.stop(job_id)

        elapsed = max(0.001, ended - started)
        avg = weighted_watts_sec / elapsed if elapsed > 0 else 0.0
        return TaskPowerReport(
            elapsed_sec=elapsed,
            avg_power_watts=max(0.0, avg),
            sampled_energy_ws=max(0.0, weighted_watts_sec),
        )


router = APIRouter()
_api_runtime: LocalPowerApi | None = None


def set_power_api_runtime(runtime: LocalPowerApi) -> None:
    global _api_runtime
    _api_runtime = runtime


@router.websocket("/internal/power/ws")
async def power_stream(ws: WebSocket):
    if _api_runtime is None:
        await ws.close(code=1011)
        return
    await _api_runtime.serve_websocket(ws)
