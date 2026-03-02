from __future__ import annotations
import asyncio, json, time
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from shared.schemas import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChoice,
    OpenAIUsage,
    OpenAIModelList,
    OpenAIModelCard,
)
from shared.utils import now_ts, new_job_id, new_req_id
from server.deps import get_db, SessionLocal
from server.api.auth_middleware import require_api_key
from server.worker_registry.service import WorkerService
from server.job_queue.service import JobService
from server.request_queue.service import AwaitingRequestService
from server.cluster.service import ClusterService
from shared.config import ServerSettings

router = APIRouter()

@router.get("/v1/models", response_model=OpenAIModelList)
def list_models(_: str = Depends(require_api_key), db: Session = Depends(get_db)):
    settings = ServerSettings()
    models = set(WorkerService(db).list_models_union())
    if settings.cluster_enabled:
        models.update(ClusterService(db).list_known_models())
    return OpenAIModelList(data=[OpenAIModelCard(id=m) for m in sorted(models)])

@router.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
async def chat_completions(
    req: OpenAIChatCompletionRequest,
    token: str = Depends(require_api_key),
    db: Session = Depends(get_db),
    x_dllm_forward_hop: int = Header(default=0, alias="X-DLLM-Forward-Hop"),
    x_dllm_seen_nodes: str = Header(default="", alias="X-DLLM-Seen-Nodes"),
):
    if req.stream:
        raise HTTPException(status_code=400, detail="stream is not supported")

    settings = ServerSettings()
    worker_svc = WorkerService(db)
    job_svc = JobService(db)
    req_svc = AwaitingRequestService(db)
    cluster_svc = ClusterService(db)
    req_id = new_req_id()
    job_id = None

    # Enqueue the request
    req_svc.create(
        req_id=req_id,
        model_name=req.model,
        payload=req.model_dump()
    )

    # Poll for assignment
    assignment_timeout_sec = float(settings.request_timeout_sec)
    poll = max(0.05, float(settings.job_poll_interval_ms) / 1000.0)
    assigned_worker_id = None

    try:
        local_has_model = worker_svc.has_online_model(req.model)
        can_forward = bool(settings.cluster_enabled) and int(x_dllm_forward_hop) < int(settings.cluster_request_max_hops)
        local_wait_budget = assignment_timeout_sec
        if can_forward:
            wait_before_forward = max(0.0, float(settings.cluster_request_forward_after_sec))
            if not local_has_model:
                local_wait_budget = 0.0
            else:
                local_wait_budget = min(local_wait_budget, wait_before_forward)
        deadline = time.time() + local_wait_budget

        while time.time() < deadline:
            await asyncio.sleep(poll)
            db2 = SessionLocal()
            try:
                awaiting_req = AwaitingRequestService(db2).get(req_id)
                if awaiting_req and awaiting_req.assigned_worker_id:
                    assigned_worker_id = awaiting_req.assigned_worker_id
                    break
            finally:
                db2.close()

        if not assigned_worker_id:
            if can_forward:
                seen = {s.strip() for s in x_dllm_seen_nodes.split(",") if s.strip()}
                seen.add(settings.cluster_node_id)
                candidates = cluster_svc.choose_forward_candidates(
                    model_name=req.model,
                    max_candidates=int(settings.cluster_request_max_candidates),
                    exclude_node_ids=seen,
                )
                headers = {
                    "Authorization": f"Bearer {token}",
                    "X-DLLM-Forward-Hop": str(int(x_dllm_forward_hop) + 1),
                    "X-DLLM-Seen-Nodes": ",".join(sorted(seen)),
                }
                forward_timeout = float(settings.cluster_request_forward_timeout_sec)
                async with httpx.AsyncClient(timeout=forward_timeout) as client:
                    for target in candidates:
                        base_url = str(target.get("base_url") or "").rstrip("/")
                        if not base_url:
                            continue
                        try:
                            resp = await client.post(
                                f"{base_url}/v1/chat/completions",
                                json=req.model_dump(),
                                headers=headers,
                            )
                        except Exception:
                            continue
                        if resp.status_code == 200:
                            return OpenAIChatCompletionResponse.model_validate(resp.json())

            raise HTTPException(status_code=503, detail=f"No available worker for model={req.model}")

        job_id = new_job_id()
        worker_svc.set_job(assigned_worker_id, job_id)

        payload = {
            "job_id": job_id,
            "model": req.model,
            "messages": [m.model_dump() for m in req.messages],
            "temperature": req.temperature,
            "top_p": req.top_p,
            "max_tokens": req.max_tokens,
            "stream": req.stream,
        }
        job_svc.create(job_id=job_id, model=req.model, assigned_worker_id=assigned_worker_id, payload=payload)

        # Poll for job completion
        job_deadline = time.time() + float(settings.job_max_wait_sec)
        while time.time() < job_deadline:
            await asyncio.sleep(poll)
            db2 = SessionLocal()
            try:
                job = JobService(db2).get(job_id)
                if not job:
                    continue
                if job.status == "done":
                    data = json.loads(job.result_json or "{}")
                    usage = OpenAIUsage(
                        prompt_tokens=int(data.get("prompt_tokens") or 0),
                        completion_tokens=int(data.get("completion_tokens") or 0),
                        total_tokens=int(data.get("total_tokens") or 0),
                    )
                    choice = OpenAIChoice(index=0, message={"role": "assistant", "content": data.get("output_text","")}, finish_reason="stop")
                    return OpenAIChatCompletionResponse(
                        id=job_id,
                        created=now_ts(),
                        model=req.model,
                        choices=[choice],
                        usage=usage,
                    )
                if job.status == "failed":
                    raise HTTPException(status_code=502, detail=f"Worker job failed: {job.error or 'unknown error'}")
            finally:
                db2.close()

        raise HTTPException(status_code=504, detail="Job timed out waiting for worker")

    finally:
        # Clean up the awaiting request and the worker's job assignment
        req_svc.delete(req_id)
        if assigned_worker_id and job_id:
            worker_svc.clear_job_if_matches(assigned_worker_id, job_id)
