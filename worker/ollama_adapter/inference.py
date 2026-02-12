from __future__ import annotations
from .client import OllamaClient

def _extract_text(resp: dict) -> str:
    msg = resp.get("message") or {}
    return msg.get("content") or ""

def _extract_tokens(resp: dict) -> tuple[int,int,int]:
    prompt = int(resp.get("prompt_eval_count") or 0)
    comp = int(resp.get("eval_count") or 0)
    return prompt, comp, prompt + comp

class OllamaInference:
    def __init__(self, client: OllamaClient):
        self.client = client

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None):
        resp = await self.client.chat(model, messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
        return _extract_text(resp), *_extract_tokens(resp)
