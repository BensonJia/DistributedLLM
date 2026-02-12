import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from server.deps import SessionLocal
from server.worker_registry.service import WorkerService
from shared.config import ServerSettings

def start_heartbeat_cleanup():
    settings = ServerSettings()
    sched = BackgroundScheduler(daemon=True)

    def _job():
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=settings.heartbeat_timeout_sec)
        db = SessionLocal()
        try:
            WorkerService(db).mark_offline_stale(cutoff)
        finally:
            db.close()

    sched.add_job(_job, "interval", seconds=settings.cleanup_interval_sec, id="worker_cleanup", replace_existing=True)
    sched.start()
    return sched
