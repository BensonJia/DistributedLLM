from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


class FastFlowLMClient:
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str] | None:
        if not self.api_key:
            return None
        return {"Authorization": f"Bearer {self.api_key}"}

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(self.base_url + "/v1/models", headers=self._headers())
            r.raise_for_status()
            data = r.json().get("data", [])
            return [{"name": item.get("id")} for item in data if item.get("id")]

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.post(self.base_url + "/v1/chat/completions", json=payload, headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def chat_stream(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float,
        top_p: float,
        max_tokens: int | None,
    ) -> AsyncIterator[dict]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                self.base_url + "/v1/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    yield json.loads(data)
