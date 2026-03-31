import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from config import DB_PATH
from database.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.close()

    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


def get_session() -> Session:
    return get_session_factory()()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database initialized.")

    from database.seed import seed_if_empty
    seed_if_empty()
