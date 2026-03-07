from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from .models import Worker, WorkerModel, WorkerModelStat
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

    def clear_job_if_matches(self, worker_id: str, expected_job_id: str):
        obj = self.db.get(Worker, worker_id)
        if not obj:
            return None
        if obj.current_job_id != expected_job_id:
            return obj
        obj.current_job_id = None
        self.db.commit()
        return obj

    def replace_worker_models(self, worker_id: str, models: list[tuple[str, float, float | None]]):
        self.db.execute(delete(WorkerModel).where(WorkerModel.worker_id == worker_id))
        for name, cost, avg_power in models:
            self.db.add(
                WorkerModel(
                    worker_id=worker_id,
                    model_name=name,
                    cost_per_token=cost,
                    avg_power_watts=avg_power,
                )
            )
        self.db.commit()

    def replace_worker_model_speeds(self, worker_id: str, model_speeds_tps: dict[str, float]):
        self.db.execute(delete(WorkerModelStat).where(WorkerModelStat.worker_id == worker_id))
        now = datetime.datetime.utcnow()
        for name, speed in model_speeds_tps.items():
            v = float(speed)
            if not name or v <= 0:
                continue
            self.db.add(
                WorkerModelStat(
                    worker_id=worker_id,
                    model_name=name,
                    speed_tps=v,
                    updated_at=now,
                )
            )
        self.db.commit()

    def list_models_union(self) -> list[str]:
        rows = self.db.execute(
            select(WorkerModel.model_name)
            .join(Worker, Worker.worker_id == WorkerModel.worker_id)
            .where(Worker.status == "online")
            .distinct()
        ).all()
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

    def has_online_model(self, model_name: str) -> bool:
        stmt = (
            select(WorkerModel.id)
            .join(Worker, Worker.worker_id == WorkerModel.worker_id)
            .where(Worker.status == "online", WorkerModel.model_name == model_name)
            .limit(1)
        )
        return self.db.execute(stmt).first() is not None
