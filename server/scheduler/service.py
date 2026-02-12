from sqlalchemy.orm import Session
from server.worker_registry.repository import WorkerRepository
from .selector import greedy_select

class SchedulerService:
    def __init__(self, db: Session):
        self.repo = WorkerRepository(db)

    def pick_worker(self, model_name: str):
        return greedy_select(self.repo.get_candidate_workers(model_name))
