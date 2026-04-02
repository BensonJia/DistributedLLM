# Worker Docker Deployment

This deployment keeps the worker in Docker while the model backend and power helper stay on the host.

## 1. Runtime Layout

- `server`: runs separately
- `worker`: runs in Docker
- `power_host`: runs on the host
- `ollama` or `fastflowlm`: runs on the host

## 2. Backend Switch

Use `DLLM_WORKER_DEFAULT_BACKEND`:

- `ollama`
- `flm`

`flm` maps to the `fastflowlm` backend internally.

Only the selected backend is exposed by the worker:

- `ollama`: only Ollama models are reported and served
- `flm`: only `DLLM_WORKER_FLM_MODELS` are reported and served

If FastFlowLM is running on the host at `http://127.0.0.1:52625/v1`, the Docker worker should use:

```env
DLLM_WORKER_DEFAULT_BACKEND=flm
DLLM_WORKER_FASTFLOWLM_URL=http://host.docker.internal:52625/v1
DLLM_WORKER_FLM_MODELS=qwen3.5:32b,qwen2.5:7b
```

When `DLLM_WORKER_DEFAULT_BACKEND=flm`, the worker heartbeat only reports models from `DLLM_WORKER_FLM_MODELS`.

## 3. Host Access Rules

- Do not point host services to `127.0.0.1` inside the container
- Use `host.docker.internal`
- On Linux, compose maps it through `host-gateway`

## 4. Environment File

Recommended `.worker_env`:

```env
DLLM_WORKER_DEFAULT_BACKEND=ollama
DLLM_WORKER_SERVER_URL=http://host.docker.internal:8000
DLLM_WORKER_INTERNAL_TOKEN=your-internal-token

DLLM_WORKER_OLLAMA_URL=http://host.docker.internal:11434
DLLM_WORKER_FASTFLOWLM_URL=http://host.docker.internal:52625/v1
DLLM_WORKER_FASTFLOWLM_API_KEY=
DLLM_WORKER_FLM_MODELS=qwen3.5:32b

DLLM_WORKER_POWER_SERVICE_HTTP_URL=http://host.docker.internal:9002
DLLM_WORKER_POWER_SERVICE_WS_URL=ws://host.docker.internal:9002/internal/power/ws
```

## 5. Deployment

Linux/macOS/Git Bash:

```bash
bash scripts/deploy_worker_docker.sh
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_worker_docker.ps1
```

## 6. Verification

```bash
curl http://127.0.0.1:9001/health
curl http://host.docker.internal:11434/api/tags
curl http://host.docker.internal:52625/v1/models
curl http://127.0.0.1:9002/health
```

If you want to use FastFlowLM for the worker, set:

```env
DLLM_WORKER_DEFAULT_BACKEND=flm
```
