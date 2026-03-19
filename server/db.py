from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from shared.config import ServerSettings

class Base(DeclarativeBase):
    pass

def make_engine(settings: ServerSettings):
    is_sqlite = settings.db_url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(
        settings.db_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=max(1, int(settings.db_pool_size)),
        max_overflow=max(0, int(settings.db_max_overflow)),
        pool_timeout=max(1.0, float(settings.db_pool_timeout_sec)),
        pool_recycle=max(60, int(settings.db_pool_recycle_sec)),
    )
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    return engine

def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
