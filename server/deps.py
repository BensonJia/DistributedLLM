from sqlalchemy.orm import Session
from sqlalchemy import text
from server.db import make_engine, make_session_factory, Base
from shared.config import ServerSettings

_settings = ServerSettings()
_engine = make_engine(_settings)
SessionLocal = make_session_factory(_engine)

def _sqlite_has_column(db, table_name: str, column_name: str) -> bool:
    rows = db.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(str(row[1]) == column_name for row in rows)

def _ensure_sqlite_schema_compat():
    if not _settings.db_url.startswith("sqlite"):
        return
    with _engine.begin() as conn:
        if not _sqlite_has_column(conn, "worker_models", "avg_power_watts"):
            conn.execute(text("ALTER TABLE worker_models ADD COLUMN avg_power_watts FLOAT"))

def init_db():
    from server.key_manager import models as _  # noqa
    from server.worker_registry import models as _  # noqa
    from server.job_queue import models as _  # noqa
    from server.request_queue import models as _ # noqa
    from server.cluster import models as _ # noqa
    Base.metadata.create_all(bind=_engine)
    _ensure_sqlite_schema_compat()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
