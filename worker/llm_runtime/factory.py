from __future__ import annotations

import os

from worker.fastflowlm_adapter.client import FastFlowLMClient
from worker.fastflowlm_adapter.inference import FastFlowLMInference
from worker.ollama_adapter.client import OllamaClient
from worker.ollama_adapter.inference import OllamaInference

from .router import BackendRoute, RoutedLLMRuntime


def _parse_routes(raw: str) -> list[BackendRoute]:
    routes: list[BackendRoute] = []
    for item in raw.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        prefix, backend_name = item.split("=", 1)
        prefix = prefix.strip()
        backend_name = backend_name.strip()
        if prefix and backend_name:
            routes.append(BackendRoute(prefix=prefix, backend_name=backend_name))
    return routes


def build_runtime(settings):
    default_backend = (os.getenv("DLLM_WORKER_DEFAULT_BACKEND", "ollama").strip() or "ollama").lower()
    route_specs = _parse_routes(os.getenv("DLLM_WORKER_BACKEND_ROUTES", "fflm/=fastflowlm"))

    backends: dict[str, object] = {
        "ollama": OllamaInference(OllamaClient(settings.ollama_url)),
    }
    backend_meta: dict[str, dict[str, str]] = {
        "ollama": {"endpoint": settings.ollama_url, "kind": "ollama"},
    }

    fastflow_url = os.getenv("DLLM_WORKER_FASTFLOWLM_URL", "").strip()
    fastflow_api_key = os.getenv("DLLM_WORKER_FASTFLOWLM_API_KEY", "").strip()
    if fastflow_url:
        backends["fastflowlm"] = FastFlowLMInference(FastFlowLMClient(fastflow_url, api_key=fastflow_api_key))
        backend_meta["fastflowlm"] = {"endpoint": fastflow_url, "kind": "fastflowlm"}

    return RoutedLLMRuntime(
        backends=backends,
        backend_meta=backend_meta,
        default_backend_name=default_backend,
        routes=route_specs,
    )
