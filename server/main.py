from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.deps import init_db, SessionLocal
from server.api.openai_compat import router as openai_router
from server.api.worker_mgmt import router as worker_router
from server.api.admin import router as admin_router
from server.background.heartbeat_timeout_checker import start_heartbeat_cleanup
from server.key_manager.service import ApiKeyService
from shared.config import ServerSettings

app = FastAPI(title="Distributed LLM Server (Pull Workers)", version="0.2.0")

settings = ServerSettings()
if settings.cors_allow_origins:
    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(settings.cors_allow_credentials),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


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
app.include_router(admin_router)

@app.get("/health")
def health():
    return {"ok": True}
