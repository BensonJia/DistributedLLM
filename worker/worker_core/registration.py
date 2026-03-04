import httpx
import logging
from shared.schemas import WorkerRegisterResponse

logger = logging.getLogger(__name__)


async def register(server_url: str, internal_token: str = "", debug: bool = False) -> str:
    url = server_url.rstrip("/") + "/internal/worker/register"
    headers = {"X-Worker-Token": internal_token} if internal_token else None
    if debug:
        logger.debug("Register request: url=%s token=%s", url, "set" if internal_token else "empty")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers)
        if debug:
            logger.debug("Register response: status=%s", r.status_code)
        r.raise_for_status()
        worker_id = WorkerRegisterResponse.model_validate(r.json()).worker_id
        if debug:
            logger.debug("Register status=ok worker_id=%s", worker_id)
        return worker_id
