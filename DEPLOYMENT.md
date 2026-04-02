# DistributedLLM Deployment Guide

This document organizes the deployment of all runtime components in one place:

- `server`: API, scheduling, worker registry
- `web`: admin UI
- `power_host`: host-side power sampling helper
- `worker`: model inference worker

## 1. Architecture

Recommended runtime layout:

1. Start `server`
2. Start `power_host` on the host machine
3. Start `worker` in Docker
4. Start `web` through the existing server deployment

The key point is:

- `worker` talks to the host Ollama service
- `worker` can switch to FastFlowLM with `DLLM_WORKER_DEFAULT_BACKEND=flm`
- `worker` only reports the FastFlowLM models listed in `DLLM_WORKER_FLM_MODELS`
- `worker` reads power data from the host-side `power_host`
- `power_host` runs on the host, not inside the worker container

The worker exposes only one backend at a time:

- `DLLM_WORKER_DEFAULT_BACKEND=ollama`: only Ollama models are available
- `DLLM_WORKER_DEFAULT_BACKEND=flm`: only `DLLM_WORKER_FLM_MODELS` are available

## 2. Ports

- `server`: `8000`
- `web`: `5173`
- `worker`: `9001`
- `power_host`: `9002`
- Ollama on host: `11434`

## 3. Prerequisites

- Docker
- Docker Compose
- Host Ollama service running and reachable on `11434`
- Network access between the worker container and the host

On Linux, this repo uses `host.docker.internal:host-gateway` in compose so the container can reach the host.

## 4. Environment Files

### 4.1 `.server_env`

Minimal example:

```env
DLLM_SERVER_API_KEYS_BOOTSTRAP=replace-with-strong-api-key
DLLM_SERVER_INTERNAL_TOKEN=replace-with-strong-internal-token
DLLM_SERVER_DB_URL=sqlite:///./data/server.db
DLLM_SERVER_PORT=8000

DLLM_WEB_PORT=5173
VITE_API_BASE=/api
VITE_PROXY_TARGET=http://dllm-server:8000
VITE_API_KEY=replace-with-strong-api-key
VITE_USE_MOCK=false

NODE_IP=127.0.0.1
NODE_INTERNAL_IP=127.0.0.1
DLLM_SERVER_CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
DLLM_SERVER_CORS_ALLOW_CREDENTIALS=false

DLLM_SERVER_CLUSTER_ENABLED=true
```

### 4.2 `.worker_env`

Minimal example:

```env
DLLM_WORKER_DEFAULT_BACKEND=ollama
DLLM_WORKER_SERVER_URL=http://host.docker.internal:8000
DLLM_WORKER_INTERNAL_TOKEN=replace-with-same-as-server-internal-token
DLLM_WORKER_OLLAMA_URL=http://host.docker.internal:11434
DLLM_WORKER_FASTFLOWLM_URL=http://host.docker.internal:52625/v1
DLLM_WORKER_FASTFLOWLM_API_KEY=
DLLM_WORKER_FLM_MODELS=qwen3.5:32b,qwen2.5:7b
DLLM_WORKER_POWER_SERVICE_HTTP_URL=http://host.docker.internal:9002
DLLM_WORKER_POWER_SERVICE_WS_URL=ws://host.docker.internal:9002/internal/power/ws

DLLM_WORKER_LISTEN_PORT=9001
DLLM_WORKER_DEBUG=false
DLLM_WORKER_HEARTBEAT_INTERVAL_SEC=20
DLLM_WORKER_JOB_POLL_INTERVAL_SEC=2
DLLM_WORKER_STREAM_INTERVAL_SEC=0.5
DLLM_WORKER_ELECTRICITY_FALLBACK_PRICE_PER_KWH=0.20
DLLM_WORKER_BASE_COST_PER_TOKEN=1e-7
DLLM_WORKER_MODEL_SIZE_MULTIPLIER=1.0
DLLM_WORKER_HOST_POWER_WATTS=250.0
```

### 4.3 `.power_env`

Minimal example:

```env
DLLM_POWER_LISTEN_PORT=9002
DLLM_POWER_SAMPLE_INTERVAL_SEC=1.0
DLLM_POWER_HOST_POWER_WATTS=250.0
DLLM_POWER_DEBUG=false
```

## 5. Deployment Order

### 5.1 Server

Linux/macOS/Git Bash:

```bash
bash scripts/deploy_server_docker.sh
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_server_docker.ps1
```

### 5.2 Power Host

Linux/macOS/Git Bash:

```bash
bash scripts/run_power_host.sh
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_power_host.ps1
```

### 5.3 Worker

Linux/macOS/Git Bash:

```bash
bash scripts/deploy_worker_docker.sh
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_worker_docker.ps1
```

## 6. Manual Docker Compose Commands

Server:

```bash
docker compose --env-file .server_env -f docker-compose.server.yml up -d --build
docker compose --env-file .server_env -f docker-compose.server.yml down
```

Worker:

```bash
docker compose --env-file .worker_env -f docker-compose.worker.yml up -d --build
docker compose --env-file .worker_env -f docker-compose.worker.yml down
```

## 7. Verification

### 7.1 Server

```bash
curl http://127.0.0.1:8000/health
```

### 7.2 Power Host

```bash
curl http://127.0.0.1:9002/health
curl http://127.0.0.1:9002/internal/power/latest
```

### 7.3 Worker

```bash
curl http://127.0.0.1:9001/health
```

### 7.4 Ollama from host

```bash
curl http://127.0.0.1:11434/api/tags
```

If the host can reach Ollama but the container cannot, check `host.docker.internal` and Docker host gateway support.

## 8. Common Pitfalls

- Do not point `DLLM_WORKER_OLLAMA_URL` to `127.0.0.1` inside the container
- Do not point `DLLM_WORKER_FASTFLOWLM_URL` to `127.0.0.1` inside the container
- Do not point `DLLM_WORKER_POWER_SERVICE_HTTP_URL` to `127.0.0.1` inside the container
- Make sure `DLLM_WORKER_INTERNAL_TOKEN` matches `DLLM_SERVER_INTERNAL_TOKEN`
- Make sure `DLLM_WORKER_FLM_MODELS` only includes models that this worker should advertise
- Make sure the host Ollama service is already running before starting the worker

## 9. Quick Checklist

1. Start Ollama on the host
2. Start `server`
3. Start `power_host`
4. Start `worker`
5. Open the web UI
