from __future__ import annotations

import logging
import os
from dataclasses import asdict
from dataclasses import replace

from fastapi import FastAPI, HTTPException
from fastapi import WebSocket

from power_host.config import PowerHostSettings
from worker.cost_engine.power_api import LocalPowerApi, PlatformPowerReader

app = FastAPI(title="Distributed LLM Power Host", version="0.1.0")
logger = logging.getLogger(__name__)

settings = PowerHostSettings()


class PowerSpikeFilter:
    def __init__(
        self,
        *,
        alpha: float = 0.25,
    ) -> None:
        self.alpha = max(0.01, min(1.0, float(alpha)))
        self._ema_total: float | None = None

    def apply(self, sample):
        raw_total = max(0.0, float(sample.total_watts))
        if self._ema_total is None:
            self._ema_total = raw_total if raw_total > 0 else float(settings.host_power_watts)
            return sample

        ema_total = (self._ema_total * (1.0 - self.alpha)) + (raw_total * self.alpha)
        self._ema_total = ema_total

        raw_components = max(0.0, float(sample.cpu_watts)) + max(0.0, float(sample.gpu_watts))
        if raw_components > 0:
            scale = ema_total / raw_components
            cpu = max(0.0, float(sample.cpu_watts) * scale)
            gpu = max(0.0, float(sample.gpu_watts) * scale)
        else:
            cpu = 0.0
            gpu = 0.0

        return replace(sample, cpu_watts=cpu, gpu_watts=gpu, total_watts=ema_total)


power_filter = PowerSpikeFilter()
power_runtime = LocalPowerApi(
    PlatformPowerReader(settings.host_power_watts, win_url=settings.win_url),
    interval_sec=settings.sample_interval_sec,
    sample_filter=power_filter.apply,
)


def _enable_debug_logging() -> None:
    if not settings.debug:
        return
    logging.getLogger("power_host").setLevel(logging.DEBUG)
    logging.getLogger("worker").setLevel(logging.DEBUG)
    logging.getLogger("shared").setLevel(logging.DEBUG)
    logger.info("Power host debug logging enabled")


def _log_startup_env() -> None:
    raw = (settings.startup_env_keys or "").strip()
    if not raw:
        return
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    for key in keys:
        value = os.environ.get(key, "<unset>")
        if "TOKEN" in key.upper() and value != "<unset>":
            value = "***"
        logger.info("startup env %s=%s", key, value)


@app.on_event("startup")
async def startup():
    _enable_debug_logging()
    logger.info(
        "Power host startup: listen_port=%s sample_interval_sec=%s host_power_watts=%s",
        settings.listen_port,
        settings.sample_interval_sec,
        settings.host_power_watts,
    )
    _log_startup_env()
    await power_runtime.start()


@app.on_event("shutdown")
async def shutdown():
    await power_runtime.stop()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/internal/power/latest")
def latest():
    sample = power_runtime.get_latest()
    if not sample:
        raise HTTPException(status_code=503, detail="power sample not ready")
    return asdict(sample)


@app.websocket("/internal/power/ws")
async def power_stream(ws: WebSocket):
    await power_runtime.serve_websocket(ws)
