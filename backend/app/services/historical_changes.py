import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change import HistoricalChange
from app.models.enums import ChangeType, Environment


def _default_demo_data_path() -> Path:
    current_file = Path(__file__).resolve()
    candidates = (
        current_file.parents[2] / "demo-data" / "historical_changes.json",
        current_file.parents[3] / "demo-data" / "historical_changes.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DEFAULT_DEMO_DATA_PATH = _default_demo_data_path()


def load_demo_records(path: Path = DEFAULT_DEMO_DATA_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Demo data file must contain a JSON array")

    return records


def seed_historical_changes(
    db: Session,
    path: Path = DEFAULT_DEMO_DATA_PATH,
) -> dict[str, int]:
    records = load_demo_records(path)
    inserted = 0
    updated = 0

    for record in records:
        record_data = dict(record)
        record_id = uuid.UUID(record_data["id"])
        record_data["id"] = record_id
        if isinstance(record_data.get("created_at"), str):
            record_data["created_at"] = datetime.fromisoformat(record_data["created_at"].replace("Z", "+00:00"))

        existing = db.get(HistoricalChange, record_id)
        if existing is None:
            db.add(HistoricalChange(**record_data))
            inserted += 1
            continue

        for field, value in record_data.items():
            setattr(existing, field, value)
        updated += 1

    db.commit()
    return {
        "inserted": inserted,
        "updated": updated,
        "total": len(records),
    }


def list_historical_changes(
    db: Session,
    environment: Environment | None = None,
    change_type: ChangeType | None = None,
    incident_occurred: bool | None = None,
    root_cause: str | None = None,
    outcome: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[HistoricalChange]:
    statement = select(HistoricalChange).order_by(HistoricalChange.created_at.desc())

    if environment is not None:
        statement = statement.where(HistoricalChange.environment == environment)
    if change_type is not None:
        statement = statement.where(HistoricalChange.change_type == change_type)
    if incident_occurred is not None:
        statement = statement.where(HistoricalChange.incident_occurred == incident_occurred)
    if root_cause is not None:
        statement = statement.where(HistoricalChange.root_cause == root_cause)
    if outcome is not None:
        statement = statement.where(HistoricalChange.outcome == outcome)

    return list(db.scalars(statement.offset(skip).limit(limit)).all())
