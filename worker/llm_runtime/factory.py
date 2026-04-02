from __future__ import annotations

import os

from worker.fastflowlm_adapter.client import FastFlowLMClient
from worker.fastflowlm_adapter.inference import FastFlowLMInference
from worker.ollama_adapter.client import OllamaClient
from worker.ollama_adapter.inference import OllamaInference

from .router import RoutedLLMRuntime


def build_runtime(settings):
    raw_default_backend = (os.getenv("DLLM_WORKER_DEFAULT_BACKEND", "ollama").strip() or "ollama").lower()
    if raw_default_backend in {"flm", "fastflowlm"}:
        default_backend = "fastflowlm"
    else:
        default_backend = "ollama"
    if default_backend == "fastflowlm":
        fastflow_url = settings.fastflowlm_url.strip()
        if not fastflow_url:
            raise ValueError("DLLM_WORKER_FASTFLOWLM_URL is required when DLLM_WORKER_DEFAULT_BACKEND=flm")
        backend = FastFlowLMInference(FastFlowLMClient(fastflow_url, api_key=settings.fastflowlm_api_key.strip()))
        backend_meta = {"endpoint": fastflow_url, "kind": "fastflowlm"}
    else:
        ollama_url = settings.ollama_url.strip()
        backend = OllamaInference(OllamaClient(ollama_url))
        backend_meta = {"endpoint": ollama_url, "kind": "ollama"}

    return RoutedLLMRuntime(backend=backend, backend_meta=backend_meta, default_backend_name=default_backend)
