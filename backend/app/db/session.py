import logging
from functools import lru_cache
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    connect_args: dict[str, int | bool] = {}

    if settings.database_url.startswith("postgresql"):
        connect_args["connect_timeout"] = settings.db_connect_timeout_seconds
    elif settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def check_database_connection() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except (OSError, SQLAlchemyError) as exc:
        logger.warning("Database connection check failed: %s", exc)
        return False


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    with session_factory() as session:
        yield session
