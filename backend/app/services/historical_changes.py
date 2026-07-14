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
        _ensure_causal_chain_fields(record_data)

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


def _ensure_causal_chain_fields(record_data: dict[str, Any]) -> None:
    if record_data.get("outcome") != "failed" and not record_data.get("incident_occurred"):
        record_data.setdefault("trigger", None)
        record_data.setdefault("technical_cause", None)
        record_data.setdefault("process_failure", None)
        record_data.setdefault("business_impact", None)
        record_data.setdefault("preventive_control", None)
        return

    root_cause = str(record_data.get("root_cause") or "unknown_dependency")
    title = str(record_data.get("title") or "change")
    lessons = str(record_data.get("lessons_learned") or "Add validation before enforcement.")
    defaults = _causal_defaults(root_cause, title, lessons)
    for field, value in defaults.items():
        record_data.setdefault(field, value)


def _causal_defaults(root_cause: str, title: str, lessons: str) -> dict[str, str]:
    process_failures = {
        "service_account_impact": "Service account inventory was incomplete before enforcement.",
        "legacy_application_dependency": "Legacy application dependency was not identified before the change.",
        "missing_exception": "Required exception was not documented before rollout.",
        "incorrect_scope": "Policy scope included identities or systems that should have been excluded.",
        "insufficient_testing": "Pilot validation did not represent production dependencies.",
        "poor_communication": "Affected users and service owners were not notified in time.",
        "rollback_failure": "Rollback procedure was not validated end-to-end.",
        "privileged_account_lockout": "Privileged access recovery was not tested before enforcement.",
        "break_glass_account_impact": "Break-glass exclusion validation was missing.",
        "timing_issue": "Implementation timing conflicted with a business-critical window.",
        "documentation_gap": "Runbook and ownership documentation were incomplete.",
        "unknown_dependency": "Dependency discovery missed a consuming system.",
    }
    technical_causes = {
        "service_account_impact": "Automation identity failed authentication after the policy changed.",
        "legacy_application_dependency": "Legacy protocol or client could not satisfy the new authentication requirement.",
        "missing_exception": "A required user, app, or account exception was absent from the policy.",
        "incorrect_scope": "The enforcement policy matched more objects than intended.",
        "insufficient_testing": "The deployment path was not validated against realistic production usage.",
        "poor_communication": "Users were blocked because operational readiness steps were missed.",
        "rollback_failure": "Rollback steps did not restore the previous service state.",
        "privileged_account_lockout": "Administrative sign-in was blocked by the new policy.",
        "break_glass_account_impact": "Emergency access account was affected by the enforcement policy.",
        "timing_issue": "The change landed during active business processing.",
        "documentation_gap": "The implementation used stale or incomplete configuration records.",
        "unknown_dependency": "An unmanaged dependency consumed the changed authentication path.",
    }
    business_impacts = {
        "service_account_impact": "Automation stopped and delayed dependent business workflows.",
        "legacy_application_dependency": "Legacy application users or jobs could not complete work.",
        "missing_exception": "Affected business users lost access until an exception or rollback was applied.",
        "incorrect_scope": "Unexpected users or systems were blocked from normal work.",
        "insufficient_testing": "Production users experienced issues that should have been caught in pilot.",
        "poor_communication": "Support volume increased and business users could not prepare.",
        "rollback_failure": "Service disruption lasted longer because recovery was delayed.",
        "privileged_account_lockout": "Administrators could not perform recovery actions immediately.",
        "break_glass_account_impact": "Emergency tenant recovery was temporarily unavailable.",
        "timing_issue": "A business-critical process was interrupted during an active window.",
        "documentation_gap": "Operators could not identify the correct owner or dependency quickly.",
        "unknown_dependency": "An undocumented business workflow was interrupted.",
    }

    return {
        "trigger": f"Change '{title}' moved from planned state to enforcement.",
        "technical_cause": technical_causes.get(root_cause, technical_causes["unknown_dependency"]),
        "process_failure": process_failures.get(root_cause, process_failures["unknown_dependency"]),
        "business_impact": business_impacts.get(root_cause, business_impacts["unknown_dependency"]),
        "preventive_control": lessons,
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
