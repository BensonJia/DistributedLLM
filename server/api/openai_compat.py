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
from shared.utils import now_ts, new_job_id
from server.deps import get_db, SessionLocal
from server.api.auth_middleware import require_api_key
from server.scheduler.service import SchedulerService
from server.worker_registry.service import WorkerService
from server.job_queue.service import JobService
from shared.config import ServerSettings

router = APIRouter()

@router.get("/v1/models", response_model=OpenAIModelList)
def list_models(_: str = Depends(require_api_key), db: Session = Depends(get_db)):
    models = WorkerService(db).list_models_union()
    return OpenAIModelList(data=[OpenAIModelCard(id=m) for m in models])

@router.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
async def chat_completions(req: OpenAIChatCompletionRequest, _: str = Depends(require_api_key), db: Session = Depends(get_db)):
    settings = ServerSettings()
    scheduler = SchedulerService(db)
    worker_svc = WorkerService(db)
    job_svc = JobService(db)

    selected = scheduler.pick_worker(req.model)
    if not selected:
        raise HTTPException(status_code=503, detail=f"No available worker for model={req.model}")

    job_id = new_job_id()
    worker_svc.set_job(selected.worker_id, job_id)

    payload = {
        "job_id": job_id,
        "model": req.model,
        "messages": [m.model_dump() for m in req.messages],
        "temperature": req.temperature,
        "top_p": req.top_p,
        "max_tokens": req.max_tokens,
        "stream": req.stream,
    }
    job_svc.create(job_id=job_id, model=req.model, assigned_worker_id=selected.worker_id, payload=payload)

    deadline = time.time() + float(settings.job_max_wait_sec)
    poll = max(0.05, float(settings.job_poll_interval_ms) / 1000.0)

    try:
        while time.time() < deadline:
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
        worker_svc.set_job(selected.worker_id, None)
