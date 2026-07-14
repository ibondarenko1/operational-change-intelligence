import os
import subprocess
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.change import Asset, AssetDependency


def test_demo_seed_endpoint_requires_demo_mode(client, monkeypatch):
    # Hermetic: assert the guard regardless of the ambient DEMO_MODE, which the
    # CI job and the README's local-dev steps both set to "true".
    monkeypatch.setenv("DEMO_MODE", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    response = client.post("/api/v1/demo/seed")

    assert response.status_code == 403


def test_demo_seed_endpoint_is_idempotent_and_filters_work(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    first_seed = client.post("/api/v1/demo/seed")
    assert first_seed.status_code == 200
    first_payload = first_seed.json()
    assert first_payload["inserted"] == 40
    assert first_payload["updated"] == 0
    assert first_payload["total"] == 40
    assert first_payload["assets_inserted"] == 17
    assert first_payload["assets_total"] == 17
    assert first_payload["dependencies_inserted"] == 12
    assert first_payload["dependencies_total"] == 12

    second_seed = client.post("/api/v1/demo/seed")
    assert second_seed.status_code == 200
    second_payload = second_seed.json()
    assert second_payload["inserted"] == 0
    assert second_payload["updated"] == 40
    assert second_payload["assets_inserted"] == 0
    assert second_payload["assets_updated"] == 17
    assert second_payload["dependencies_inserted"] == 0
    assert second_payload["dependencies_updated"] == 12

    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(Asset)) == 17
        assert db.scalar(select(func.count()).select_from(AssetDependency)) == 12

    all_changes = client.get("/api/v1/historical-changes")
    assert all_changes.status_code == 200
    assert len(all_changes.json()) == 40

    failed_changes = client.get("/api/v1/historical-changes?outcome=failed")
    assert failed_changes.status_code == 200
    assert len(failed_changes.json()) == 17

    incident_changes = client.get("/api/v1/historical-changes?incident_occurred=true")
    assert incident_changes.status_code == 200
    assert len(incident_changes.json()) == 17

    mfa_changes = client.get("/api/v1/historical-changes?change_type=mfa_rollout")
    assert mfa_changes.status_code == 200
    assert len(mfa_changes.json()) == 5

    missing_exception = client.get("/api/v1/historical-changes?root_cause=missing_exception")
    assert missing_exception.status_code == 200
    assert len(missing_exception.json()) == 2

    defender_successes = client.get(
        "/api/v1/historical-changes?environment=defender&outcome=successful"
    )
    assert defender_successes.status_code == 200
    assert len(defender_successes.json()) == 3


def test_seed_script_is_idempotent(tmp_path):
    db_path = tmp_path / "seed_script.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+pysqlite:///{db_path}",
        "APP_CHECK_DB_ON_STARTUP": "false",
    }

    command = [sys.executable, "scripts/seed_demo_data.py", "--create-tables"]

    first = subprocess.run(
        command,
        cwd="..",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "inserted=40 updated=0 total=40" in first.stdout

    second = subprocess.run(
        command,
        cwd="..",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "inserted=0 updated=40 total=40" in second.stdout
