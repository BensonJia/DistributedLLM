from sqlalchemy.orm import Session
from server.db import make_engine, make_session_factory, Base
from shared.config import ServerSettings

_settings = ServerSettings()
_engine = make_engine(_settings)
SessionLocal = make_session_factory(_engine)

def init_db():
    from server.key_manager import models as _  # noqa
    from server.worker_registry import models as _  # noqa
    from server.job_queue import models as _  # noqa
    from server.request_queue import models as _ # noqa
    from server.cluster import models as _ # noqa
    Base.metadata.create_all(bind=_engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
