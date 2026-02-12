import httpx

class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(self.base_url + "/api/tags")
            r.raise_for_status()
            return r.json().get("models", [])

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None):
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "top_p": top_p},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = int(max_tokens)
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.post(self.base_url + "/api/chat", json=payload)
            r.raise_for_status()
            return r.json()
