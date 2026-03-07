from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _JobChannel:
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    closed: bool = False


class JobStreamHub:
    def __init__(self) -> None:
        self._channels: dict[str, _JobChannel] = {}
        self._lock = asyncio.Lock()

    async def ensure(self, job_id: str) -> None:
        async with self._lock:
            self._channels.setdefault(job_id, _JobChannel())

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        async with self._lock:
            ch = self._channels.setdefault(job_id, _JobChannel())
            return ch.queue

    async def publish_delta(self, job_id: str, delta: str) -> None:
        async with self._lock:
            ch = self._channels.get(job_id)
            if not ch or ch.closed:
                return
            await ch.queue.put({"type": "delta", "delta": delta})

    async def publish_error(self, job_id: str, message: str) -> None:
        async with self._lock:
            ch = self._channels.get(job_id)
            if not ch or ch.closed:
                return
            await ch.queue.put({"type": "error", "message": message})

    async def publish_done(self, job_id: str, usage: dict[str, Any] | None = None) -> None:
        async with self._lock:
            ch = self._channels.get(job_id)
            if not ch or ch.closed:
                return
            await ch.queue.put({"type": "done", "usage": usage or {}})

    async def close(self, job_id: str) -> None:
        async with self._lock:
            ch = self._channels.get(job_id)
            if not ch:
                return
            ch.closed = True
            self._channels.pop(job_id, None)


job_stream_hub = JobStreamHub()

