from server.scheduler.selector import WorkerCandidate, greedy_select, rank_candidates


def test_rank_candidates_prioritizes_workers_missing_perf_data():
    candidates = [
        WorkerCandidate(worker_id="warm-fast", cost_per_token=0.2, speed_tps=30.0),
        WorkerCandidate(worker_id="cold-no-speed", cost_per_token=0.1, speed_tps=0.0),
        WorkerCandidate(worker_id="warm-cheap", cost_per_token=0.1, speed_tps=20.0),
        WorkerCandidate(worker_id="cold-no-cost", cost_per_token=0.0, speed_tps=10.0),
    ]

    ranked = rank_candidates(candidates, speed_tolerance_ratio=0.1)
    ranked_ids = [c.worker_id for c in ranked]

    assert ranked_ids[:2] == ["cold-no-cost", "cold-no-speed"]


def test_rank_candidates_keeps_existing_strategy_for_warm_workers():
    candidates = [
        WorkerCandidate(worker_id="a", cost_per_token=0.2, speed_tps=100.0),
        WorkerCandidate(worker_id="b", cost_per_token=0.1, speed_tps=95.0),
        WorkerCandidate(worker_id="c", cost_per_token=0.01, speed_tps=50.0),
    ]

    ranked = rank_candidates(candidates, speed_tolerance_ratio=0.1)
    ranked_ids = [c.worker_id for c in ranked]

    assert ranked_ids == ["b", "a", "c"]


def test_greedy_select_picks_missing_data_worker_first():
    candidates = [
        WorkerCandidate(worker_id="warm", cost_per_token=0.1, speed_tps=20.0),
        WorkerCandidate(worker_id="cold", cost_per_token=0.1, speed_tps=0.0),
    ]

    selected = greedy_select(candidates, speed_tolerance_ratio=0.1)

    assert selected is not None
    assert selected.worker_id == "cold"
