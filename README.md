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

## Admin endpoints (for Admin UI)
These endpoints require `Authorization: Bearer <api_key>`:
- GET `/admin/workers`
- GET `/admin/workers/{worker_id}`
- GET `/admin/jobs`
- GET `/admin/jobs/{job_id}`

## Optional CORS (for browser-based UI)
- `DLLM_SERVER_CORS_ALLOW_ORIGINS` (comma-separated, e.g. `http://localhost:5173,https://admin.example.com`)
- `DLLM_SERVER_CORS_ALLOW_CREDENTIALS` (`true`/`false`)

## Optional internal worker auth
To protect internal worker endpoints, set the same token on server and worker:
- `DLLM_SERVER_INTERNAL_TOKEN`
- `DLLM_WORKER_INTERNAL_TOKEN`

When `DLLM_SERVER_INTERNAL_TOKEN` is empty, internal endpoints keep backward-compatible behavior (no token required).

## Optional decentralized server federation (gossip + latency-aware forwarding)
Enable inter-server federation on every server node:

- `DLLM_SERVER_CLUSTER_ENABLED=true`
- `DLLM_SERVER_CLUSTER_NODE_ID=<unique-node-id>`
- `DLLM_SERVER_CLUSTER_SELF_URL=http(s)://<this-node-domain>`
- `DLLM_SERVER_CLUSTER_SEED_URLS=http(s)://seed-a,http(s)://seed-b`
- `DLLM_SERVER_INTERNAL_TOKEN=<shared-cluster-token>`

Request routing behavior when federation is enabled:
- Current node still tries local workers first.
- If requested model is not locally available, or local assignment exceeds `DLLM_SERVER_CLUSTER_REQUEST_FORWARD_AFTER_SEC`, the request is forwarded to low-latency neighbor nodes that advertise this model.
- Forwarding hop limit is controlled by `DLLM_SERVER_CLUSTER_REQUEST_MAX_HOPS`.

Useful tuning knobs:
- `DLLM_SERVER_CLUSTER_NEIGHBOR_COUNT` (latency probe set size)
- `DLLM_SERVER_CLUSTER_GOSSIP_FANOUT` (neighbors per gossip round)
- `DLLM_SERVER_CLUSTER_GOSSIP_INTERVAL_SEC`
- `DLLM_SERVER_CLUSTER_DELTA_BATCH_SIZE`
- `DLLM_SERVER_CLUSTER_REQUEST_MAX_CANDIDATES`
