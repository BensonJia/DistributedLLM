from __future__ import annotations

from typing import Awaitable, Callable


class RoutedLLMRuntime:
    def __init__(
        self,
        *,
        backend: object,
        backend_meta: dict[str, str],
        default_backend_name: str,
    ):
        self.backend = backend
        self.backend_meta = backend_meta
        self.default_backend_name = default_backend_name

    def describe(self) -> dict[str, object]:
        return {
            "default_backend": self.default_backend_name,
            "backends": {self.default_backend_name: self.backend_meta},
        }

    async def list_models(self) -> list[dict]:
        return await self.backend.client.list_models()

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None):
        return await self.backend.chat(
            model,
            messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

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
        return await self.backend.chat_stream(
            model,
            messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            on_delta=on_delta,
        )
