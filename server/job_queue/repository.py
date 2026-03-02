from __future__ import annotations
import json, datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from .models import Job

class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_job(self, *, job_id: str, model: str, assigned_worker_id: str, payload: dict) -> Job:
        obj = Job(
            job_id=job_id,
            status="pending",
            model=model,
            assigned_worker_id=assigned_worker_id,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def lease_next_for_worker(self, worker_id: str) -> Job | None:
        now = datetime.datetime.utcnow()
        target_id = (
            select(Job.id)
            .where(Job.status == "pending", Job.assigned_worker_id == worker_id)
            .order_by(Job.created_at.asc())
            .limit(1)
            .scalar_subquery()
        )
        # Atomic lease: claim exactly one pending row and return it.
        stmt = (
            update(Job)
            .where(Job.id == target_id, Job.status == "pending")
            .values(status="running", updated_at=now)
            .returning(Job)
        )
        job = self.db.execute(stmt).scalar_one_or_none()
        if not job:
            self.db.rollback()
            return None
        self.db.commit()
        return job

    def complete_job(self, job_id: str, result: dict, error: str | None = None) -> Job | None:
        job = self.db.execute(select(Job).where(Job.job_id == job_id)).scalar_one_or_none()
        if not job:
            return None
        job.status = "done" if not error else "failed"
        job.result_json = json.dumps(result, ensure_ascii=False) if result is not None else None
        job.error = error
        job.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.db.execute(select(Job).where(Job.job_id == job_id)).scalar_one_or_none()
