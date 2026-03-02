import httpx
from shared.schemas import WorkerRegisterResponse

async def register(server_url: str, internal_token: str = "") -> str:
    url = server_url.rstrip("/") + "/internal/worker/register"
    headers = {"X-Worker-Token": internal_token} if internal_token else None
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers)
        r.raise_for_status()
        return WorkerRegisterResponse.model_validate(r.json()).worker_id
