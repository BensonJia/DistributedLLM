from fastapi import FastAPI
from server.deps import init_db, SessionLocal
from server.api.openai_compat import router as openai_router
from server.api.worker_mgmt import router as worker_router
from server.background.heartbeat_timeout_checker import start_heartbeat_cleanup
from server.key_manager.service import ApiKeyService
from shared.config import ServerSettings

app = FastAPI(title="Distributed LLM Server (Pull Workers)", version="0.2.0")

@app.on_event("startup")
def startup():
    init_db()
    settings = ServerSettings()
    if settings.api_keys_bootstrap:
        db = SessionLocal()
        try:
            ApiKeyService(db).bootstrap(settings.api_keys_bootstrap)
        finally:
            db.close()
    start_heartbeat_cleanup()

app.include_router(openai_router)
app.include_router(worker_router)

@app.get("/health")
def health():
    return {"ok": True}
