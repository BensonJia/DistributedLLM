from __future__ import annotations

from typing import Awaitable, Callable

from .client import FastFlowLMClient


def _extract_text(resp: dict) -> str:
    choices = resp.get("choices") or []
    if not choices:
        return ""
    choice = choices[0] or {}
    delta = choice.get("delta") or {}
    if "content" in delta:
        return delta.get("content") or ""
    msg = choice.get("message") or {}
    return msg.get("content") or ""


def _extract_tokens(resp: dict) -> tuple[int, int, int]:
    usage = resp.get("usage") or {}
    prompt = int(usage.get("prompt_tokens") or 0)
    comp = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + comp))
    return prompt, comp, total


class FastFlowLMInference:
    def __init__(self, client: FastFlowLMClient):
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
            prompt_tokens, completion_tokens, total_tokens = _extract_tokens(resp)

        return "".join(out_parts), prompt_tokens, completion_tokens, total_tokens
