from __future__ import annotations
import httpx
import logging
from shared.schemas import WorkerHeartbeat, WorkerModelInfo

logger = logging.getLogger(__name__)


class HeartbeatReporter:
    def __init__(self, server_url: str, internal_token: str = "", debug: bool = False):
        self.server_url = server_url.rstrip("/")
        self.internal_token = internal_token
        self.debug = debug

    def _headers(self) -> dict[str, str] | None:
        if not self.internal_token:
            return None
        return {"X-Worker-Token": self.internal_token}

    async def send(self, hb: WorkerHeartbeat):
        url = self.server_url + "/internal/worker/heartbeat"
        if self.debug:
            logger.debug(
                "Comm[heartbeat] request: worker_id=%s status=%s current_job_id=%s",
                hb.worker_id,
                hb.status,
                hb.current_job_id,
            )
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=hb.model_dump(), headers=self._headers())
            if self.debug:
                logger.debug("Comm[heartbeat] response: status=%s", r.status_code)
            r.raise_for_status()
            return r.json()

def build_heartbeat(worker_id: str, state, meta: dict | None = None) -> WorkerHeartbeat:
    return WorkerHeartbeat(
        worker_id=worker_id,
        status=state.status,
        current_job_id=state.current_job_id,
        models=[WorkerModelInfo(name=n, cost_per_token=c, avg_power_watts=p) for n, c, p in state.models],
        loaded_model=state.loaded_model,
        meta=meta or {},
    )
