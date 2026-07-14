import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change import ChangeRequest
from app.schemas.change import ChangeRequestCreate, ChangeRequestUpdate


class ChangeRequestNotFoundError(Exception):
    pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_change_request(db: Session, payload: ChangeRequestCreate) -> ChangeRequest:
    change_request = ChangeRequest(**payload.model_dump())
    db.add(change_request)
    db.commit()
    db.refresh(change_request)
    return change_request


def list_change_requests(db: Session, skip: int = 0, limit: int = 100) -> Sequence[ChangeRequest]:
    statement = select(ChangeRequest).order_by(ChangeRequest.created_at.desc()).offset(skip).limit(limit)
    return db.scalars(statement).all()


def get_change_request(db: Session, change_request_id: uuid.UUID) -> ChangeRequest:
    change_request = db.get(ChangeRequest, change_request_id)
    if change_request is None:
        raise ChangeRequestNotFoundError
    return change_request


def update_change_request(
    db: Session,
    change_request_id: uuid.UUID,
    payload: ChangeRequestUpdate,
) -> ChangeRequest:
    change_request = get_change_request(db, change_request_id)
    update_data = payload.model_dump(exclude_unset=True)

    planned_start = update_data.get("planned_start", change_request.planned_start)
    planned_end = update_data.get("planned_end", change_request.planned_end)
    if _as_utc(planned_end) < _as_utc(planned_start):
        raise ValueError("planned_end cannot be earlier than planned_start")

    for field, value in update_data.items():
        setattr(change_request, field, value)

    db.add(change_request)
    db.commit()
    db.refresh(change_request)
    return change_request


def delete_change_request(db: Session, change_request_id: uuid.UUID) -> None:
    change_request = get_change_request(db, change_request_id)
    db.delete(change_request)
    db.commit()
