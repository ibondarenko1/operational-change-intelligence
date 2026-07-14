from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, get_engine
from app.main import app
from app.models.base import Base


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("APP_CHECK_DB_ON_STARTUP", "false")
    get_settings.cache_clear()
    get_engine.cache_clear()

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine, autoflush=False, autocommit=False, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()
