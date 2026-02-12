import httpx
from shared.schemas import WorkerRegisterResponse

async def register(server_url: str) -> str:
    url = server_url.rstrip("/") + "/internal/worker/register"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url)
        r.raise_for_status()
        return WorkerRegisterResponse.model_validate(r.json()).worker_id
