from __future__ import annotations
import httpx
from shared.schemas import WorkerJobPullRequest, WorkerJobPullResponse, WorkerJobCompleteRequest

class JobPullClient:
    def __init__(self, server_url: str, internal_token: str = ""):
        self.server_url = server_url.rstrip("/")
        self.internal_token = internal_token

    def _headers(self) -> dict[str, str] | None:
        if not self.internal_token:
            return None
        return {"X-Worker-Token": self.internal_token}

    async def pull(self, worker_id: str) -> WorkerJobPullResponse | None:
        url = self.server_url + "/internal/job/pull"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                json=WorkerJobPullRequest(worker_id=worker_id).model_dump(),
                headers=self._headers(),
            )
            if r.status_code == 204:
                return None
            r.raise_for_status()
            return WorkerJobPullResponse.model_validate(r.json())

    async def complete(self, payload: WorkerJobCompleteRequest):
        url = self.server_url + "/internal/job/complete"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload.model_dump(), headers=self._headers())
            r.raise_for_status()
            return r.json()
