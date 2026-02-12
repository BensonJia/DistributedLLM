from __future__ import annotations
import httpx
from shared.schemas import WorkerJobPullRequest, WorkerJobPullResponse, WorkerJobCompleteRequest

class JobPullClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")

    async def pull(self, worker_id: str) -> WorkerJobPullResponse | None:
        url = self.server_url + "/internal/job/pull"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=WorkerJobPullRequest(worker_id=worker_id).model_dump())
            if r.status_code == 204:
                return None
            r.raise_for_status()
            return WorkerJobPullResponse.model_validate(r.json())

    async def complete(self, payload: WorkerJobCompleteRequest):
        url = self.server_url + "/internal/job/complete"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload.model_dump())
            r.raise_for_status()
            return r.json()
