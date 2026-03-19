from apscheduler.schedulers.background import BackgroundScheduler
import logging
from server.deps import SessionLocal
from server.request_queue.service import AwaitingRequestService
from server.scheduler.service import SchedulerService
from server.worker_registry.service import WorkerService
from shared.config import ServerSettings

logger = logging.getLogger(__name__)

def start_request_assigner():
    settings = ServerSettings()
    sched = BackgroundScheduler(daemon=True)

    def _job():
        db = SessionLocal()
        try:
            req_service = AwaitingRequestService(db)
            scheduler = SchedulerService(db)
            worker_service = WorkerService(db)
            pending_reqs = req_service.get_pending()

            if not pending_reqs:
                return

            logger.info(f"Request assigner found {len(pending_reqs)} pending requests.")

            model_names = sorted({str(req.model_name) for req in pending_reqs if req.model_name})
            worker_pool_by_model: dict[str, list] = {}
            for model_name in model_names:
                worker_pool_by_model[model_name] = scheduler.list_ranked_workers(
                    model_name,
                    speed_tolerance_ratio=float(settings.scheduler_speed_tolerance_ratio),
                )

            claimed_workers: set[str] = set()
            assigned_count = 0

            # Requests are already ordered by model then created_at in repository.
            for req in pending_reqs:
                model_name = str(req.model_name)
                ranked_workers = worker_pool_by_model.get(model_name) or []
                while ranked_workers:
                    selected = ranked_workers.pop(0)
                    worker_id = str(selected.worker_id)
                    if worker_id in claimed_workers:
                        continue
                    reserved = worker_service.reserve_job_if_idle(worker_id, req.req_id)
                    if not reserved:
                        continue
                    assigned = req_service.assign_worker(req.req_id, worker_id)
                    if assigned:
                        claimed_workers.add(worker_id)
                        assigned_count += 1
                        logger.info(
                            "Assigned worker=%s req_id=%s model=%s speed_tps=%.4f cost_per_token=%.8f",
                            worker_id,
                            req.req_id,
                            model_name,
                            float(selected.speed_tps),
                            float(selected.cost_per_token),
                        )
                        break
                    worker_service.clear_job_if_matches(worker_id, req.req_id)
            if assigned_count:
                logger.info("Request assigner batch complete: assigned=%s pending=%s", assigned_count, len(pending_reqs))
        except Exception:
            logger.exception("Error in request assigner job")
        finally:
            db.close()

    sched.add_job(
        _job,
        "interval",
        seconds=float(settings.dispatch_interval_sec),
        id="request_assigner",
        replace_existing=True,
    )
    sched.start()
    logger.info("Request assigner background job started.")
    return sched
