from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class BackendRoute:
    prefix: str
    backend_name: str


class RoutedLLMRuntime:
    def __init__(
        self,
        *,
        backends: dict[str, object],
        backend_meta: dict[str, dict[str, str]],
        default_backend_name: str,
        routes: list[BackendRoute],
    ):
        self.backends = backends
        self.backend_meta = backend_meta
        self.default_backend_name = default_backend_name
        self.routes = sorted(routes, key=lambda item: len(item.prefix), reverse=True)

        if default_backend_name not in backends:
            raise ValueError(f"Default backend '{default_backend_name}' is not configured")
        for route in self.routes:
            if route.backend_name not in backends:
                raise ValueError(f"Backend '{route.backend_name}' is not configured for prefix '{route.prefix}'")

    def describe(self) -> dict[str, object]:
        advertised_routes = [{"prefix": route.prefix, "backend": route.backend_name} for route in self.routes]
        return {
            "default_backend": self.default_backend_name,
            "routes": advertised_routes,
            "backends": self.backend_meta,
        }

    def _resolve(self, model: str) -> tuple[object, str]:
        for route in self.routes:
            if model.startswith(route.prefix):
                backend_model = model[len(route.prefix):]
                if not backend_model:
                    raise ValueError(f"Model '{model}' is missing the backend model name after prefix '{route.prefix}'")
                return self.backends[route.backend_name], backend_model
        return self.backends[self.default_backend_name], model

    async def list_models(self) -> list[dict]:
        merged: dict[str, dict] = {}
        seen: set[tuple[str, str]] = set()

        for route in self.routes:
            route_key = (route.backend_name, route.prefix)
            if route_key in seen:
                continue
            seen.add(route_key)
            backend = self.backends[route.backend_name]
            raw_models = await backend.client.list_models()
            for item in raw_models:
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                merged[route.prefix + name] = {"name": route.prefix + name}

        default_backend = self.backends[self.default_backend_name]
        default_models = await default_backend.client.list_models()
        for item in default_models:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            merged.setdefault(name, {"name": name})

        return [merged[name] for name in sorted(merged)]

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None):
        backend, backend_model = self._resolve(model)
        return await backend.chat(
            backend_model,
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
        backend, backend_model = self._resolve(model)
        return await backend.chat_stream(
            backend_model,
            messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            on_delta=on_delta,
        )
