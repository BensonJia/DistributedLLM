from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SelectedWorker:
    worker_id: str
    cost_per_token: float

def greedy_select(candidates: list[tuple[object, float]]) -> SelectedWorker | None:
    if not candidates:
        return None
    best_worker, best_cost = min(candidates, key=lambda x: float(x[1]))
    return SelectedWorker(worker_id=best_worker.worker_id, cost_per_token=float(best_cost))
