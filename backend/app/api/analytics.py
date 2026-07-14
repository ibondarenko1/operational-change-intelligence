from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import ChangeType, Environment
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    ChangeTypeAnalyticsResponse,
    FailurePatternResponse,
    RootCauseAnalyticsResponse,
)
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/root-causes", response_model=list[RootCauseAnalyticsResponse])
def get_root_cause_analytics(
    environment: Environment | None = None,
    change_type: ChangeType | None = None,
    db: Session = Depends(get_db),
) -> list[RootCauseAnalyticsResponse]:
    return AnalyticsService().get_root_causes(db, environment=environment, change_type=change_type)


@router.get("/change-types", response_model=list[ChangeTypeAnalyticsResponse])
def get_change_type_analytics(
    environment: Environment | None = None,
    change_type: ChangeType | None = None,
    db: Session = Depends(get_db),
) -> list[ChangeTypeAnalyticsResponse]:
    return AnalyticsService().get_change_types(db, environment=environment, change_type=change_type)


@router.get("/failure-patterns", response_model=list[FailurePatternResponse])
def get_failure_patterns(
    environment: Environment | None = None,
    change_type: ChangeType | None = None,
    db: Session = Depends(get_db),
) -> list[FailurePatternResponse]:
    return AnalyticsService().get_failure_patterns(db, environment=environment, change_type=change_type)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_summary(
    environment: Environment | None = None,
    change_type: ChangeType | None = None,
    db: Session = Depends(get_db),
) -> AnalyticsSummaryResponse:
    return AnalyticsService().get_summary(db, environment=environment, change_type=change_type)
