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


def _extract_eval_speed_tps(resp: dict) -> float | None:
    usage = resp.get("usage") or {}
    eval_count = int(resp.get("eval_count") or usage.get("eval_count") or 0)
    eval_duration = int(resp.get("eval_duration") or usage.get("eval_duration") or 0)
    if eval_count <= 0 or eval_duration <= 0:
        return None
    seconds = float(eval_duration) / 1_000_000_000.0
    if seconds <= 0:
        return None
    speed = float(eval_count) / seconds
    return speed if speed > 0 else None


class FastFlowLMInference:
    def __init__(self, client: FastFlowLMClient):
        self.client = client

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None):
        resp = await self.client.chat(model, messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
        return _extract_text(resp), *_extract_tokens(resp), _extract_eval_speed_tps(resp)

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
        eval_speed_tps: float | None = None

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
            eval_speed_tps = _extract_eval_speed_tps(resp)

        return "".join(out_parts), prompt_tokens, completion_tokens, total_tokens, eval_speed_tps
