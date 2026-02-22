from __future__ import annotations
import asyncio, json, time
from fastapi import APIRouter, Depends, HTTPException
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
from shared.config import ServerSettings

router = APIRouter()

@router.get("/v1/models", response_model=OpenAIModelList)
def list_models(_: str = Depends(require_api_key), db: Session = Depends(get_db)):
    models = WorkerService(db).list_models_union()
    return OpenAIModelList(data=[OpenAIModelCard(id=m) for m in models])

@router.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
async def chat_completions(req: OpenAIChatCompletionRequest, _: str = Depends(require_api_key), db: Session = Depends(get_db)):
    settings = ServerSettings()
    worker_svc = WorkerService(db)
    job_svc = JobService(db)
    req_svc = AwaitingRequestService(db)
    req_id = new_req_id()

    # Enqueue the request
    req_svc.create(
        req_id=req_id,
        model_name=req.model,
        payload=req.model_dump_json()
    )

    # Poll for assignment
    deadline = time.time() + 30.0  # 30 second timeout for worker assignment
    poll = max(0.05, float(settings.job_poll_interval_ms) / 1000.0)
    assigned_worker_id = None

    try:
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
            raise HTTPException(status_code=503, detail=f"No available worker for model={req.model} within 30s")

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
        if assigned_worker_id:
            worker_svc.set_job(assigned_worker_id, None)