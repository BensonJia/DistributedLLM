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

router = APIRouter()

@router.post("/internal/worker/register", response_model=WorkerRegisterResponse)
def register_worker():
    return WorkerRegisterResponse(worker_id=new_worker_id())

@router.post("/internal/worker/heartbeat")
async def heartbeat(payload: WorkerHeartbeat, db: Session = Depends(get_db)):
    WorkerService(db).handle_heartbeat(payload)
    return {"ok": True}

@router.post("/internal/job/pull", response_model=WorkerJobPullResponse)
def pull_job(payload: WorkerJobPullRequest, db: Session = Depends(get_db)):
    job = JobService(db).lease_for_worker(payload.worker_id)
    if not job:
        return Response(status_code=204)
    data = json.loads(job.payload_json)
    return WorkerJobPullResponse.model_validate(data)

@router.post("/internal/job/complete")
def complete_job(payload: WorkerJobCompleteRequest, db: Session = Depends(get_db)):
    JobService(db).complete(payload.job_id, result=payload.model_dump(), error=payload.error)
    WorkerService(db).set_job(payload.worker_id, None)
    return {"ok": True}
