from sqlalchemy.orm import Session
from server.worker_registry.repository import WorkerRepository
from .selector import WorkerCandidate, SelectedWorker, greedy_select, rank_candidates

class SchedulerService:
    def __init__(self, db: Session):
        self.repo = WorkerRepository(db)

    def list_ranked_workers(self, model_name: str, *, speed_tolerance_ratio: float) -> list[SelectedWorker]:
        rows = self.repo.get_candidate_workers_with_speed(model_name)
        candidates: list[WorkerCandidate] = []
        for worker, cost_per_token, speed_tps in rows:
            candidates.append(
                WorkerCandidate(
                    worker_id=str(worker.worker_id),
                    cost_per_token=float(cost_per_token),
                    speed_tps=float(speed_tps or 0.0),
                )
            )
        ranked = rank_candidates(candidates, speed_tolerance_ratio=speed_tolerance_ratio)
        return [
            SelectedWorker(
                worker_id=c.worker_id,
                cost_per_token=float(c.cost_per_token),
                speed_tps=max(0.0, float(c.speed_tps)),
            )
            for c in ranked
        ]

    def pick_worker(self, model_name: str, *, speed_tolerance_ratio: float = 0.0):
        rows = self.repo.get_candidate_workers_with_speed(model_name)
        candidates: list[WorkerCandidate] = []
        for worker, cost_per_token, speed_tps in rows:
            candidates.append(
                WorkerCandidate(
                    worker_id=str(worker.worker_id),
                    cost_per_token=float(cost_per_token),
                    speed_tps=float(speed_tps or 0.0),
                )
            )
        return greedy_select(candidates, speed_tolerance_ratio=speed_tolerance_ratio)
