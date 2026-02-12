from __future__ import annotations
from sqlalchemy.orm import Session
from .repository import JobRepository

class JobService:
    def __init__(self, db: Session):
        self.repo = JobRepository(db)

    def create(self, job_id: str, model: str, assigned_worker_id: str, payload: dict):
        return self.repo.create_job(job_id=job_id, model=model, assigned_worker_id=assigned_worker_id, payload=payload)

    def lease_for_worker(self, worker_id: str):
        return self.repo.lease_next_for_worker(worker_id)

    def complete(self, job_id: str, result: dict, error: str | None = None):
        return self.repo.complete_job(job_id, result, error=error)

    def get(self, job_id: str):
        return self.repo.get_job(job_id)
