import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.change import ChecklistItem, HistoricalChange, RiskAssessment, RiskFactor
from app.services.change_requests import ChangeRequestNotFoundError, get_change_request
from app.services.demo_assets import attach_demo_assets_to_change, build_asset_context
from app.services.impact_analysis import ImpactAnalysisResult, ImpactAnalysisService
from app.services.risk_engine import RiskAssessmentResult, RiskEngine
from app.services.similarity import SimilarHistoricalChange


class RiskAssessmentNotFoundError(Exception):
    pass


def analyze_change_request(
    db: Session,
    change_request_id: uuid.UUID,
    risk_engine: RiskEngine | None = None,
) -> RiskAssessment:
    change_request = get_change_request(db, change_request_id)
    historical_changes = _get_historical_changes(db)
    engine = risk_engine or RiskEngine()
    change_assets = attach_demo_assets_to_change(db, change_request)
    impact_result = ImpactAnalysisService().analyze(db, change_request, change_assets)
    asset_context = build_asset_context(change_assets)
    similar_changes = engine.similarity_service.find_similar(
        change_request,
        historical_changes,
        limit=min(max(len(historical_changes), 1), 20),
        asset_context=asset_context,
    )
    result = engine.analyze(
        change_request,
        historical_changes,
        asset_context=asset_context,
        similar_changes=similar_changes,
    )

    existing_assessments = db.scalars(
        select(RiskAssessment)
        .options(selectinload(RiskAssessment.risk_factors), selectinload(RiskAssessment.checklist_items))
        .where(RiskAssessment.change_request_id == change_request_id)
    ).all()
    for existing_assessment in existing_assessments:
        db.delete(existing_assessment)
    db.flush()

    assessment = _create_assessment_model(change_request_id, result, impact_result, similar_changes)
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


def _create_assessment_model(
    change_request_id: uuid.UUID,
    result: RiskAssessmentResult,
    impact_result: ImpactAnalysisResult,
    similar_changes: list[SimilarHistoricalChange],
) -> RiskAssessment:
    assessment = RiskAssessment(
        change_request_id=change_request_id,
        score=result.score,
        raw_score=result.raw_score,
        capped_score=result.capped_score,
        level=result.level,
        recommendation=result.recommendation,
        confidence=result.confidence,
        category_scores=result.category_scores,
        formula_explanation=result.formula_explanation,
        similar_changes=[_similar_change_payload(item) for item in similar_changes[:10]],
        directly_affected_assets=impact_result.directly_affected_assets,
        dependent_assets=impact_result.dependent_assets,
        affected_business_services=impact_result.affected_business_services,
        impact_paths=impact_result.impact_paths,
        predicted_failure_modes=impact_result.predicted_failure_modes,
        blast_radius=impact_result.blast_radius,
        missing_context=impact_result.missing_context,
    )
    assessment.risk_factors = [
        RiskFactor(
            code=factor.code,
            title=factor.title,
            description=factor.description,
            category=factor.category,
            category_cap=factor.category_cap,
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


def _similar_change_payload(similar_change: SimilarHistoricalChange) -> dict:
    return {
        "historical_change_id": str(similar_change.historical_change_id),
        "title": similar_change.title,
        "similarity_score": similar_change.similarity_score,
        "matching_factors": similar_change.matching_factors,
        "outcome": similar_change.outcome,
        "incident_occurred": similar_change.incident_occurred,
        "root_cause": similar_change.root_cause,
        "downtime_minutes": similar_change.downtime_minutes,
        "rollback_required": similar_change.rollback_required,
        "lessons_learned": similar_change.lessons_learned,
        "historical_failure_signal": similar_change.historical_failure_signal,
        "historical_severity": similar_change.historical_severity,
    }
