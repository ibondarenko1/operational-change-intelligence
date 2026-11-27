import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.change import Asset, AssetDependency


def _ignore_quickstart_files(_directory: str, names: list[str]) -> set[str]:
    ignored = {".venv", "venv", "env", "__pycache__", ".pytest_cache", ".ruff_cache"}
    return {
        name
        for name in names
        if name in ignored or Path(name).suffix in {".db", ".pyc"}
    }


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


def test_documented_sqlite_quickstart_uses_one_working_directory(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    quickstart_root = tmp_path / "quickstart"
    copy_options = {"ignore": _ignore_quickstart_files}
    shutil.copytree(repo_root / "backend", quickstart_root / "backend", **copy_options)
    shutil.copytree(repo_root / "scripts", quickstart_root / "scripts", **copy_options)
    shutil.copytree(repo_root / "demo-data", quickstart_root / "demo-data", **copy_options)

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    local_backend_section = readme.split("## Local Backend", maxsplit=1)[1].split(
        "## Local Frontend", maxsplit=1
    )[0]
    command_block = re.search(r"```powershell\n(?P<commands>.*?)```", local_backend_section, re.DOTALL)
    assert command_block is not None

    env = dict(os.environ)
    working_directory = quickstart_root
    seed = None
    for raw_line in command_block.group("commands").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        change_directory = re.fullmatch(r"cd\s+(.+)", line)
        if change_directory:
            working_directory = (working_directory / change_directory.group(1)).resolve()
            continue
        environment_assignment = re.fullmatch(r'\$env:(\w+)\s*=\s*"(.*)"', line)
        if environment_assignment:
            env[environment_assignment.group(1)] = environment_assignment.group(2)
            continue
        if line.startswith("python -m pip install"):
            continue
        if line.startswith("python -m alembic "):
            command = [sys.executable, "-m", "alembic", *line.split()[3:]]
        elif line.startswith("python ") and "uvicorn" not in line:
            script = line.removeprefix("python ").replace("\\", "/")
            command = [sys.executable, *script.split()]
        elif line.startswith("python -m uvicorn "):
            break
        else:
            raise AssertionError(f"Unsupported quickstart command: {line}")
        completed = subprocess.run(
            command,
            cwd=working_directory,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        if "seed_demo_data.py" in line:
            seed = completed

    assert seed is not None

    assert "inserted=40 updated=0 total=40" in seed.stdout
    backend_root = quickstart_root / "backend"
    assert (backend_root / "local_dev.db").exists()
    assert not (quickstart_root / "local_dev.db").exists()

    monkeypatch.chdir(working_directory)
    monkeypatch.setenv("DATABASE_URL", env["DATABASE_URL"])
    monkeypatch.setenv("APP_CHECK_DB_ON_STARTUP", "false")
    from app.core.config import get_settings
    from app.db.session import get_engine
    from app.main import create_app

    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        with TestClient(create_app()) as api_client:
            response = api_client.get("/api/v1/historical-changes?outcome=failed")
        assert response.status_code == 200
        assert len(response.json()) == 17
    finally:
        get_engine.cache_clear()
        get_settings.cache_clear()
