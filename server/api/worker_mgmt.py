from __future__ import annotations
import json
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from shared.schemas import (
    WorkerRegisterResponse,
    WorkerHeartbeat,
    WorkerJobPullRequest,
    WorkerJobPullResponse,
    WorkerJobCompleteRequest,
)
from shared.utils import new_worker_id
from server.deps import get_db
from server.worker_registry.service import WorkerService
from server.job_queue.service import JobService
from server.api.auth_middleware import require_internal_token

router = APIRouter()

@router.post("/internal/worker/register", response_model=WorkerRegisterResponse)
def register_worker(_: str = Depends(require_internal_token)):
    return WorkerRegisterResponse(worker_id=new_worker_id())

@router.post("/internal/worker/heartbeat")
async def heartbeat(payload: WorkerHeartbeat, _: str = Depends(require_internal_token), db: Session = Depends(get_db)):
    WorkerService(db).handle_heartbeat(payload)
    return {"ok": True}

@router.post("/internal/job/pull", response_model=WorkerJobPullResponse)
def pull_job(payload: WorkerJobPullRequest, _: str = Depends(require_internal_token), db: Session = Depends(get_db)):
    job = JobService(db).lease_for_worker(payload.worker_id)
    if not job:
        return Response(status_code=204)
    data = json.loads(job.payload_json)
    return WorkerJobPullResponse.model_validate(data)

@router.post("/internal/job/complete")
def complete_job(payload: WorkerJobCompleteRequest, _: str = Depends(require_internal_token), db: Session = Depends(get_db)):
    JobService(db).complete(payload.job_id, result=payload.model_dump(), error=payload.error)
    WorkerService(db).clear_job_if_matches(payload.worker_id, payload.job_id)
    return {"ok": True}
