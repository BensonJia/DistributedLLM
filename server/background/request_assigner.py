from apscheduler.schedulers.background import BackgroundScheduler
import logging
from server.deps import SessionLocal
from server.request_queue.service import AwaitingRequestService
from server.scheduler.service import SchedulerService

logger = logging.getLogger(__name__)

def start_request_assigner():
    sched = BackgroundScheduler(daemon=True)

    def _job():
        db = SessionLocal()
        try:
            req_service = AwaitingRequestService(db)
            scheduler = SchedulerService(db)
            pending_reqs = req_service.get_pending()
            
            if not pending_reqs:
                return

            logger.info(f"Request assigner found {len(pending_reqs)} pending requests.")
            
            # This is a simple 1-to-1 assignment.
            # A more complex logic could consider available workers and pending requests together.
            for req in pending_reqs:
                selected = scheduler.pick_worker(req.model_name)
                if selected:
                    worker_id, _ = selected
                    logger.info(f"Assigning worker {worker_id} to request {req.req_id} for model {req.model_name}")
                    req_service.assign_worker(req.req_id, worker_id)
        except Exception:
            logger.exception("Error in request assigner job")
        finally:
            db.close()

    # Run this job frequently to ensure requests are picked up quickly.
    sched.add_job(_job, "interval", seconds=2, id="request_assigner", replace_existing=True)
    sched.start()
    logger.info("Request assigner background job started.")
    return sched
