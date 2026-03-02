from __future__ import annotations
from sqlalchemy.orm import Session
from .repository import WorkerRepository
from shared.schemas import WorkerHeartbeat

class WorkerService:
    def __init__(self, db: Session):
        self.repo = WorkerRepository(db)

    def handle_heartbeat(self, hb: WorkerHeartbeat):
        current_job = hb.current_job_id if hb.status == "busy" else None
        self.repo.upsert_worker(hb.worker_id, status="online", current_job_id=current_job)
        models = [(m.name, float(m.cost_per_token)) for m in hb.models]
        self.repo.replace_worker_models(hb.worker_id, models)

    def mark_offline_stale(self, cutoff_dt):
        return self.repo.set_offline_if_stale(cutoff_dt)

    def set_job(self, worker_id: str, job_id: str | None):
        return self.repo.set_job(worker_id, job_id)

    def clear_job_if_matches(self, worker_id: str, expected_job_id: str):
        return self.repo.clear_job_if_matches(worker_id, expected_job_id)

    def list_models_union(self):
        return self.repo.list_models_union()

    def has_online_model(self, model_name: str) -> bool:
        return self.repo.has_online_model(model_name)
