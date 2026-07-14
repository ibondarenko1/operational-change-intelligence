import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.change import ChecklistItem, HistoricalChange, RiskAssessment, RiskFactor
from app.services.change_requests import ChangeRequestNotFoundError, get_change_request
from app.services.demo_assets import get_demo_asset_context
from app.services.risk_engine import RiskAssessmentResult, RiskEngine


class RiskAssessmentNotFoundError(Exception):
    pass


def analyze_change_request(
    db: Session,
    change_request_id: uuid.UUID,
    risk_engine: RiskEngine | None = None,
) -> RiskAssessment:
    change_request = get_change_request(db, change_request_id)
    historical_changes = _get_historical_changes(db)
    result = (risk_engine or RiskEngine()).analyze(
        change_request,
        historical_changes,
        asset_context=get_demo_asset_context(change_request),
    )

    existing_assessments = db.scalars(
        select(RiskAssessment)
        .options(selectinload(RiskAssessment.risk_factors), selectinload(RiskAssessment.checklist_items))
        .where(RiskAssessment.change_request_id == change_request_id)
    ).all()
    for existing_assessment in existing_assessments:
        db.delete(existing_assessment)
    db.flush()

    assessment = _create_assessment_model(change_request_id, result)
    db.add(assessment)
    db.commit()

    return get_change_assessment(db, change_request_id)


def get_change_assessment(db: Session, change_request_id: uuid.UUID) -> RiskAssessment:
    try:
        get_change_request(db, change_request_id)
    except ChangeRequestNotFoundError:
        raise

    statement = (
        select(RiskAssessment)
        .options(selectinload(RiskAssessment.risk_factors), selectinload(RiskAssessment.checklist_items))
        .where(RiskAssessment.change_request_id == change_request_id)
        .order_by(RiskAssessment.created_at.desc())
    )
    assessment = db.scalars(statement).first()
    if assessment is None:
        raise RiskAssessmentNotFoundError
    return assessment


def _get_historical_changes(db: Session) -> list[HistoricalChange]:
    return list(db.scalars(select(HistoricalChange)).all())


def _create_assessment_model(change_request_id: uuid.UUID, result: RiskAssessmentResult) -> RiskAssessment:
    assessment = RiskAssessment(
        change_request_id=change_request_id,
        score=result.score,
        level=result.level,
        recommendation=result.recommendation,
        confidence=result.confidence,
    )
    assessment.risk_factors = [
        RiskFactor(
            code=factor.code,
            title=factor.title,
            description=factor.description,
            points=factor.points,
            evidence=factor.evidence,
        )
        for factor in result.risk_factors
    ]
    assessment.checklist_items = [
        ChecklistItem(
            code=item.code,
            title=item.title,
            description=item.description,
            priority=item.priority,
            status=item.status,
        )
        for item in result.checklist_items
    ]
    return assessment
