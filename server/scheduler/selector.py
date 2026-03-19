from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SelectedWorker:
    worker_id: str
    cost_per_token: float
    speed_tps: float

@dataclass(frozen=True)
class WorkerCandidate:
    worker_id: str
    cost_per_token: float
    speed_tps: float

def _has_missing_perf_data(candidate: WorkerCandidate) -> bool:
    speed = max(0.0, float(candidate.speed_tps))
    cost = float(candidate.cost_per_token)
    return speed <= 0.0 or cost <= 0.0


def rank_candidates(
    candidates: list[WorkerCandidate],
    *,
    speed_tolerance_ratio: float,
) -> list[WorkerCandidate]:
    if not candidates:
        return []

    cold_start = [c for c in candidates if _has_missing_perf_data(c)]
    warm = [c for c in candidates if not _has_missing_perf_data(c)]
    cold_start.sort(key=lambda c: (c.worker_id, float(c.cost_per_token)))

    if not warm:
        return cold_start

    tol = max(0.0, float(speed_tolerance_ratio))
    max_speed = max(max(0.0, float(c.speed_tps)) for c in warm)
    speed_floor = max_speed * max(0.0, 1.0 - tol)

    within_tolerance: list[WorkerCandidate] = []
    slower: list[WorkerCandidate] = []
    for c in warm:
        speed = max(0.0, float(c.speed_tps))
        if speed >= speed_floor:
            within_tolerance.append(c)
        else:
            slower.append(c)

    # Within speed tolerance: prioritize lower cost first, then faster speed.
    within_tolerance.sort(key=lambda c: (float(c.cost_per_token), -max(0.0, float(c.speed_tps)), c.worker_id))
    # Outside speed tolerance: prioritize faster workers first, then lower cost.
    slower.sort(key=lambda c: (-max(0.0, float(c.speed_tps)), float(c.cost_per_token), c.worker_id))
    return cold_start + within_tolerance + slower


def greedy_select(
    candidates: list[WorkerCandidate],
    *,
    speed_tolerance_ratio: float,
) -> SelectedWorker | None:
    ranked = rank_candidates(candidates, speed_tolerance_ratio=speed_tolerance_ratio)
    if not ranked:
        return None
    best = ranked[0]
    return SelectedWorker(
        worker_id=best.worker_id,
        cost_per_token=float(best.cost_per_token),
        speed_tps=max(0.0, float(best.speed_tps)),
    )
