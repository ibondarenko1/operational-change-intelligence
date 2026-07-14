from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models.change import ChangeRequest, HistoricalChange
from app.models.enums import ChangeStatus, ChangeType, Environment
from app.services.risk_engine import RiskEngine
from app.services.similarity import SimilarityService


CONTRACTORS_FAILURE_ID = UUID("00000000-0000-4000-8000-000000000002")


def make_change(**overrides) -> ChangeRequest:
    values = {
        "id": uuid4(),
        "title": "Enable MFA for all contractors",
        "description": "Require MFA registration for contractor and vendor accounts before access enforcement.",
        "environment": Environment.entra_id,
        "change_type": ChangeType.mfa_rollout,
        "planned_start": datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
        "planned_end": datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
        "affected_scope": "All contractors and vendor accounts",
        "rollback_plan": "Disable the contractor MFA policy and restore the previous optional MFA assignment.",
        "maintenance_window": True,
        "pilot_enabled": False,
        "report_only_mode": False,
        "status": ChangeStatus.draft,
    }
    values.update(overrides)
    return ChangeRequest(**values)


def make_historical(**overrides) -> HistoricalChange:
    values = {
        "id": uuid4(),
        "title": "MFA enforcement for all contractors",
        "description": (
            "Changed contractor sign-in policy from optional MFA to required MFA. Several shared vendor "
            "accounts could not complete registration."
        ),
        "environment": Environment.entra_id,
        "change_type": ChangeType.mfa_rollout,
        "outcome": "failed",
        "incident_occurred": True,
        "downtime_minutes": 95,
        "rollback_required": True,
        "root_cause": "missing_exception",
        "lessons_learned": "Review vendor-operated shared accounts and create exceptions before broad MFA enforcement.",
    }
    values.update(overrides)
    return HistoricalChange(**values)


def test_similarity_results_are_ranked_by_score():
    change = make_change()
    relevant_failed = make_historical(id=CONTRACTORS_FAILURE_ID)
    same_type_success = make_historical(
        title="Phased MFA rollout for finance users",
        description="Enabled Microsoft Authenticator push MFA for the finance department after a two-week pilot.",
        outcome="successful",
        incident_occurred=False,
        downtime_minutes=0,
        rollback_required=False,
        root_cause=None,
        lessons_learned="Piloting with payroll approvers avoided impact.",
    )
    unrelated_success = make_historical(
        title="Defender policy tuning for servers",
        description="Updated endpoint detection exclusions for a small server group.",
        environment=Environment.defender,
        change_type=ChangeType.defender_policy_change,
        outcome="successful",
        incident_occurred=False,
        downtime_minutes=0,
        rollback_required=False,
        root_cause=None,
        lessons_learned="Server owners validated the policy.",
    )

    results = SimilarityService().find_similar(
        change,
        [unrelated_success, same_type_success, relevant_failed],
        limit=3,
    )

    assert [result.historical_change_id for result in results] == [
        relevant_failed.id,
        same_type_success.id,
        unrelated_success.id,
    ]
    assert all(0 <= result.similarity_score <= 1 for result in results)
    assert "environment=entra_id" in results[0].matching_factors
    assert "change_type=mfa_rollout" in results[0].matching_factors


def test_similar_failed_change_scores_above_irrelevant_successful_change():
    change = make_change()
    relevant_failed = make_historical(id=CONTRACTORS_FAILURE_ID)
    irrelevant_success = make_historical(
        title="Guest access review cleanup",
        description="Removed stale guest access invitations after owner approval.",
        environment=Environment.microsoft_365,
        change_type=ChangeType.guest_access_change,
        outcome="successful",
        incident_occurred=False,
        downtime_minutes=0,
        rollback_required=False,
        root_cause=None,
        lessons_learned="Ownership review was completed before cleanup.",
    )

    service = SimilarityService()
    failed_score = service.score_historical_change(change, relevant_failed).similarity_score
    success_score = service.score_historical_change(change, irrelevant_success).similarity_score

    assert failed_score > success_score
    assert failed_score >= 0.8


def test_similarity_sorting_is_independent_from_historical_outcome():
    change = make_change(
        description="Require MFA for contractor accounts using Microsoft 365 and legacy VPN access.",
        affected_scope="All contractor accounts, service accounts, VPN, and legacy applications",
    )
    highly_similar_success = make_historical(
        title="Enable MFA for all contractors",
        description=(
            "Required MFA for all contractor accounts, service accounts, VPN access, and legacy applications "
            "after a pilot and report-only phase."
        ),
        outcome="successful",
        incident_occurred=False,
        downtime_minutes=0,
        rollback_required=False,
        root_cause=None,
    )
    less_similar_failure = make_historical(
        title="Device compliance incident for sales laptops",
        description="A failed Intune compliance policy blocked unmanaged sales devices.",
        environment=Environment.azure,
        change_type=ChangeType.device_compliance,
        outcome="failed",
        incident_occurred=True,
        downtime_minutes=180,
        rollback_required=True,
        root_cause="insufficient_testing",
    )

    results = SimilarityService().find_similar(change, [less_similar_failure, highly_similar_success], limit=2)

    assert results[0].historical_change_id == highly_similar_success.id
    assert results[0].similarity_score > results[1].similarity_score
    assert results[0].outcome == "successful"
    assert results[1].historical_failure_signal is True
    assert not any("incident" in factor for factor in results[1].matching_factors)


def test_similarity_increases_risk_assessment_score():
    change = make_change()
    relevant_failed = make_historical(id=CONTRACTORS_FAILURE_ID)
    irrelevant_success = make_historical(
        title="Defender policy tuning for servers",
        description="Updated endpoint detection exclusions for a small server group.",
        environment=Environment.defender,
        change_type=ChangeType.defender_policy_change,
        outcome="successful",
        incident_occurred=False,
        downtime_minutes=0,
        rollback_required=False,
        root_cause=None,
        lessons_learned="Server owners validated the policy.",
    )

    without_history = RiskEngine().analyze(change, [])
    with_history = RiskEngine().analyze(change, [irrelevant_success, relevant_failed])
    factor = next(factor for factor in with_history.risk_factors if factor.code == "similar_failures_found")

    assert with_history.score > without_history.score
    assert factor.points > 0
    assert "MFA enforcement for all contractors" in factor.evidence
