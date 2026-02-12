# Distributed LLM (OpenAI-compatible) — Pull-based Workers (NAT friendly)

This version is **NAT-friendly**: the **server never calls workers**.
Workers **heartbeat** (online/models/costs) and **pull jobs** from the server, run Ollama inference, then **push results** back.

## Quick start

### 1) Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run server
```bash
export DLLM_SERVER_DB_URL=sqlite:///./server.db
export DLLM_SERVER_API_KEYS_BOOTSTRAP=dev-key-123
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 3) Run worker (behind NAT is OK)
Requires **Ollama** running locally (default `http://127.0.0.1:11434`).
```bash
export DLLM_WORKER_SERVER_URL=http://<server-ip>:8000
export DLLM_WORKER_OLLAMA_URL=http://127.0.0.1:11434
python -m uvicorn worker.main:app --host 0.0.0.0 --port 9001
```
Worker will auto-register, heartbeat, and pull jobs in background.

### 4) Call OpenAI-compatible endpoint
```bash
curl http://<server-ip>:8000/v1/chat/completions   -H "Authorization: Bearer dev-key-123"   -H "Content-Type: application/json"   -d '{
    "model": "qwen3:8b",
    "messages": [{"role":"user","content":"用中文回答：1+1等于几？"}],
    "temperature": 0.2
  }'
```

## How routing works
- Server picks a worker with greedy strategy: **lowest `cost_per_token`** among **online + idle** workers supporting the requested model.
- Server enqueues a job assigned to that worker.
- Worker pulls `/internal/job/pull`, executes via Ollama, and posts `/internal/job/complete`.

## Notes
- Electricity price provider is pluggable:
  - default fallback price `0.2` (currency/kWh)
  - optional: set `DLLM_WORKER_ELECTRICITY_URL` to a local service returning `{"price_per_kwh": 0.18}`
