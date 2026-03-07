from __future__ import annotations
from .client import OllamaClient
from typing import Awaitable, Callable

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

    async def chat_stream(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float,
        top_p: float,
        max_tokens: int | None,
        on_delta: Callable[[str], Awaitable[None]],
    ):
        out_parts: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        async for resp in self.client.chat_stream(
            model,
            messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        ):
            delta = _extract_text(resp)
            if delta:
                out_parts.append(delta)
                await on_delta(delta)
            if bool(resp.get("done")):
                prompt_tokens, completion_tokens, total_tokens = _extract_tokens(resp)

        return "".join(out_parts), prompt_tokens, completion_tokens, total_tokens
