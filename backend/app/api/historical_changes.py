from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import ChangeType, Environment
from app.schemas.change import HistoricalChangeResponse
from app.services.historical_changes import list_historical_changes

router = APIRouter(prefix="/api/v1/historical-changes", tags=["historical-changes"])


@router.get("", response_model=list[HistoricalChangeResponse])
def get_historical_changes(
    environment: Environment | None = None,
    change_type: ChangeType | None = None,
    incident_occurred: bool | None = None,
    root_cause: str | None = None,
    outcome: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[HistoricalChangeResponse]:
    return list_historical_changes(
        db,
        environment=environment,
        change_type=change_type,
        incident_occurred=incident_occurred,
        root_cause=root_cause,
        outcome=outcome,
        skip=skip,
        limit=limit,
    )
