from __future__ import annotations
import httpx
from shared.schemas import WorkerHeartbeat, WorkerModelInfo

class HeartbeatReporter:
    def __init__(self, server_url: str, internal_token: str = ""):
        self.server_url = server_url.rstrip("/")
        self.internal_token = internal_token

    def _headers(self) -> dict[str, str] | None:
        if not self.internal_token:
            return None
        return {"X-Worker-Token": self.internal_token}

    async def send(self, hb: WorkerHeartbeat):
        url = self.server_url + "/internal/worker/heartbeat"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=hb.model_dump(), headers=self._headers())
            r.raise_for_status()
            return r.json()

def build_heartbeat(worker_id: str, state, meta: dict | None = None) -> WorkerHeartbeat:
    return WorkerHeartbeat(
        worker_id=worker_id,
        status=state.status,
        current_job_id=state.current_job_id,
        models=[WorkerModelInfo(name=n, cost_per_token=c) for n, c in state.models],
        loaded_model=state.loaded_model,
        meta=meta or {},
    )
