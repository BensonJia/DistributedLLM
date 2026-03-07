from __future__ import annotations
import httpx
import logging
from shared.schemas import WorkerJobPullRequest, WorkerJobPullResponse, WorkerJobCompleteRequest, WorkerJobChunkRequest

logger = logging.getLogger(__name__)


class JobPullClient:
    def __init__(self, server_url: str, internal_token: str = "", debug: bool = False):
        self.server_url = server_url.rstrip("/")
        self.internal_token = internal_token
        self.debug = debug

    def _headers(self) -> dict[str, str] | None:
        if not self.internal_token:
            return None
        return {"X-Worker-Token": self.internal_token}

    async def pull(self, worker_id: str) -> WorkerJobPullResponse | None:
        url = self.server_url + "/internal/job/pull"
        if self.debug:
            logger.debug("Comm[pull] request: worker_id=%s url=%s", worker_id, url)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                json=WorkerJobPullRequest(worker_id=worker_id).model_dump(),
                headers=self._headers(),
            )
            if self.debug:
                logger.debug("Comm[pull] response: status=%s", r.status_code)
            if r.status_code == 204:
                return None
            r.raise_for_status()
            return WorkerJobPullResponse.model_validate(r.json())

    async def complete(self, payload: WorkerJobCompleteRequest):
        url = self.server_url + "/internal/job/complete"
        if self.debug:
            logger.debug("Comm[complete] request: job_id=%s url=%s", payload.job_id, url)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload.model_dump(), headers=self._headers())
            if self.debug:
                logger.debug("Comm[complete] response: status=%s job_id=%s", r.status_code, payload.job_id)
            r.raise_for_status()
            return r.json()

    async def chunk(self, payload: WorkerJobChunkRequest):
        url = self.server_url + "/internal/job/chunk"
        if self.debug:
            logger.debug("Comm[chunk] request: job_id=%s url=%s", payload.job_id, url)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload.model_dump(), headers=self._headers())
            if self.debug:
                logger.debug("Comm[chunk] response: status=%s job_id=%s", r.status_code, payload.job_id)
            r.raise_for_status()
            return r.json()
