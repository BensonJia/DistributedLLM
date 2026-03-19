from __future__ import annotations

import pytest

from worker.llm_runtime.router import BackendRoute, RoutedLLMRuntime


class _StubClient:
    def __init__(self, names: list[str]):
        self._names = names

    async def list_models(self) -> list[dict]:
        return [{"name": name} for name in self._names]


class _StubBackend:
    def __init__(self, names: list[str]):
        self.client = _StubClient(names)
        self.last_model: str | None = None

    async def chat(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None):
        self.last_model = model
        return "ok", 1, 2, 3

    async def chat_stream(self, model: str, messages: list[dict], *, temperature: float, top_p: float, max_tokens: int | None, on_delta):
        self.last_model = model
        await on_delta("x")
        return "x", 1, 1, 2


@pytest.mark.asyncio
async def test_list_models_applies_prefix_routes():
    runtime = RoutedLLMRuntime(
        backends={
            "ollama": _StubBackend(["qwen3:8b"]),
            "fastflowlm": _StubBackend(["vision-7b"]),
        },
        backend_meta={},
        default_backend_name="ollama",
        routes=[BackendRoute(prefix="fflm/", backend_name="fastflowlm")],
    )

    models = await runtime.list_models()

    assert models == [{"name": "fflm/vision-7b"}, {"name": "qwen3:8b"}]


@pytest.mark.asyncio
async def test_chat_strips_prefix_before_routing():
    fastflow = _StubBackend(["vision-7b"])
    runtime = RoutedLLMRuntime(
        backends={
            "ollama": _StubBackend(["qwen3:8b"]),
            "fastflowlm": fastflow,
        },
        backend_meta={},
        default_backend_name="ollama",
        routes=[BackendRoute(prefix="fflm/", backend_name="fastflowlm")],
    )

    await runtime.chat("fflm/vision-7b", [], temperature=0.7, top_p=1.0, max_tokens=None)

    assert fastflow.last_model == "vision-7b"


def test_runtime_rejects_missing_default_backend():
    with pytest.raises(ValueError, match="Default backend"):
        RoutedLLMRuntime(
            backends={},
            backend_meta={},
            default_backend_name="ollama",
            routes=[],
        )
