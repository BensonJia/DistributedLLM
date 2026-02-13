# Distributed LLM Admin UI (Vue 3 + Material-ish CSS)

A modular Vue3 SPA for managing:
- Workers (status/models/costs/current job)
- Jobs (status timeline, assignment, result)

## Run locally
```bash
npm install
npm run dev
```

## Configure backend
Create `.env.local`:
```bash
VITE_API_BASE=http://localhost:8000
# Optional (recommended): use Bearer key for any endpoints that require it
VITE_API_KEY=dev-key-123
# Optional: start with mock data
VITE_USE_MOCK=false
```

## Backend API expectations (admin endpoints)
The current backend version exposes:
- `GET /health`
- `GET /v1/models` (requires Authorization: Bearer <api_key>)
- `POST /v1/chat/completions` (requires Authorization)
- Worker internal:
  - `POST /internal/worker/register`
  - `POST /internal/worker/heartbeat`
  - `POST /internal/job/pull`
  - `POST /internal/job/complete`

For this Admin UI to be fully functional, it expects these **admin endpoints** as well:
- `GET /admin/workers`
- `GET /admin/workers/{worker_id}`
- `GET /admin/jobs`
- `GET /admin/jobs/{job_id}`

If these endpoints are missing or return 404, the UI can fall back to **Mock mode** (`VITE_USE_MOCK=true`).
