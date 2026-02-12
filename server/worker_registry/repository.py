from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from .models import Worker, WorkerModel
import datetime

class WorkerRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_worker(self, worker_id: str, *, status: str, current_job_id: str | None):
        obj = self.db.get(Worker, worker_id)
        if not obj:
            obj = Worker(worker_id=worker_id)
            self.db.add(obj)
        obj.status = status
        obj.current_job_id = current_job_id
        obj.last_heartbeat = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def set_offline_if_stale(self, cutoff_dt: datetime.datetime):
        q = self.db.execute(select(Worker).where(Worker.last_heartbeat < cutoff_dt, Worker.status == "online"))
        changed = 0
        for w in q.scalars().all():
            w.status = "offline"
            w.current_job_id = None
            changed += 1
        if changed:
            self.db.commit()
        return changed

    def set_job(self, worker_id: str, job_id: str | None):
        obj = self.db.get(Worker, worker_id)
        if not obj:
            return None
        obj.current_job_id = job_id
        self.db.commit()
        return obj

    def replace_worker_models(self, worker_id: str, models: list[tuple[str, float]]):
        self.db.execute(delete(WorkerModel).where(WorkerModel.worker_id == worker_id))
        for name, cost in models:
            self.db.add(WorkerModel(worker_id=worker_id, model_name=name, cost_per_token=cost))
        self.db.commit()

    def list_models_union(self) -> list[str]:
        rows = self.db.execute(select(WorkerModel.model_name).distinct()).all()
        return sorted({r[0] for r in rows if r[0]})

    def get_candidate_workers(self, model_name: str):
        stmt = (
            select(Worker, WorkerModel.cost_per_token)
            .join(WorkerModel, Worker.worker_id == WorkerModel.worker_id)
            .where(
                Worker.status == "online",
                Worker.current_job_id.is_(None),
                WorkerModel.model_name == model_name,
            )
        )
        return self.db.execute(stmt).all()
