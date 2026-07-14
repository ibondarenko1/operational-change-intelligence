from datetime import UTC, datetime
from uuid import uuid4

from app.models.change import ChangeRequest, HistoricalChange
from app.models.enums import ChangeStatus, ChangeType, Environment
from app.services.demo_assets import get_demo_asset_context
from app.services.risk_engine import FORMULA, RiskEngine


def make_change(**overrides) -> ChangeRequest:
    values = {
        "id": uuid4(),
        "title": "Targeted policy update",
        "description": "Update policy for pilot group members.",
        "environment": Environment.entra_id,
        "change_type": ChangeType.conditional_access,
        "planned_start": datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        "planned_end": datetime(2026, 8, 1, 11, 0, tzinfo=UTC),
        "affected_scope": "Pilot group A",
        "rollback_plan": "Disable the new policy and restore the previous assignment group.",
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
        "title": "Failed conditional access rollout",
        "description": "Previous rollout caused user sign-in failures.",
        "environment": Environment.entra_id,
        "change_type": ChangeType.conditional_access,
        "outcome": "failed",
        "incident_occurred": True,
        "downtime_minutes": 45,
        "rollback_required": True,
        "root_cause": "missing_exception",
        "lessons_learned": "Pilot changes against service owners before enforcement.",
    }
    values.update(overrides)
    return HistoricalChange(**values)


def factor_by_code(result, code: str):
    return next(factor for factor in result.risk_factors if factor.code == code)


def test_privileged_accounts_affected_rule():
    result = RiskEngine().analyze(make_change(affected_scope="Privileged role administrators"))

    factor = factor_by_code(result, "privileged_accounts_affected")
    assert factor.points == 25
    assert "privileged role" in factor.evidence


def test_service_accounts_affected_rule():
    result = RiskEngine().analyze(make_change(description="Policy affects automation service accounts."))

    factor = factor_by_code(result, "service_accounts_affected")
    assert factor.points == 20
    assert "service account" in factor.evidence


def test_rollback_plan_missing_rule():
    result = RiskEngine().analyze(make_change(rollback_plan="TBD"))

    factor = factor_by_code(result, "rollback_plan_missing")
    assert factor.points == 20
    assert "TBD" in factor.evidence
    assert "weak_rollback_validation" not in {risk_factor.code for risk_factor in result.risk_factors}


def test_short_rollback_plan_uses_weak_validation_not_missing_rule():
    result = RiskEngine().analyze(make_change(rollback_plan="Disable the new policy."))
    factor_codes = {risk_factor.code for risk_factor in result.risk_factors}

    assert "rollback_plan_missing" not in factor_codes
    assert "weak_rollback_validation" in factor_codes


def test_full_tested_rollback_does_not_add_rollback_validation_risk():
    result = RiskEngine().analyze(
        make_change(
            rollback_plan=(
                "Disable the new policy, restore the previous assignment group, validate contractor "
                "and admin sign-ins, monitor failures for thirty minutes, and attach tested rollback evidence."
            )
        )
    )
    factor_codes = {risk_factor.code for risk_factor in result.risk_factors}

    assert "rollback_plan_missing" not in factor_codes
    assert "weak_rollback_validation" not in factor_codes
    assert "tested_rollback" in factor_codes


def test_broad_scope_rule():
    result = RiskEngine().analyze(make_change(affected_scope="All users in the production tenant"))

    factor = factor_by_code(result, "broad_scope")
    assert factor.points == 15
    assert "all users" in factor.evidence


def test_legacy_applications_present_rule():
    result = RiskEngine().analyze(make_change(description="Block legacy IMAP and POP clients."))

    factor = factor_by_code(result, "legacy_applications_present")
    assert factor.points == 15
    assert "legacy" in factor.evidence


def test_outside_maintenance_window_rule():
    result = RiskEngine().analyze(make_change(maintenance_window=False))

    factor = factor_by_code(result, "outside_maintenance_window")
    assert factor.points == 10
    assert "maintenance_window is false" in factor.evidence


def test_similar_failures_found_rule_caps_at_twenty_points():
    histories = [make_historical(title=f"Failed rollout {index}") for index in range(5)]

    result = RiskEngine().analyze(make_change(), histories)

    factor = factor_by_code(result, "similar_failures_found")
    assert factor.points == 20
    assert "5 similar failed historical changes" in factor.evidence


def test_missing_pilot_rule_adds_risk():
    result = RiskEngine().analyze(make_change(pilot_enabled=False))

    factor = factor_by_code(result, "pilot_missing")
    assert factor.points == 15
    assert "pilot_enabled is false" in factor.evidence


def test_missing_report_only_rule_adds_risk():
    result = RiskEngine().analyze(make_change(report_only_mode=False))

    factor = factor_by_code(result, "report_only_missing")
    assert factor.points == 10
    assert "report_only_mode is false" in factor.evidence


def test_weak_rollback_validation_rule_adds_risk():
    result = RiskEngine().analyze(make_change(rollback_plan="Disable the new policy."))

    factor = factor_by_code(result, "weak_rollback_validation")
    assert factor.points == 15
    assert "lacks validation detail" in factor.evidence


def test_pilot_enabled_rule_reduces_risk():
    result = RiskEngine().analyze(make_change(pilot_enabled=True))

    factor = factor_by_code(result, "pilot_enabled")
    assert factor.points == -15


def test_report_only_mode_rule_reduces_risk():
    result = RiskEngine().analyze(make_change(report_only_mode=True))

    factor = factor_by_code(result, "report_only_mode")
    assert factor.points == -10


def test_tested_rollback_rule_reduces_risk():
    result = RiskEngine().analyze(
        make_change(rollback_plan="Disable policy, verified rollback in staging, and validate sign-ins.")
    )

    factor = factor_by_code(result, "tested_rollback")
    assert factor.points == -10


def test_risk_level_recommendation_and_formula_are_explicit():
    result = RiskEngine().analyze(
        make_change(
            title="Tenant-wide legacy authentication block for admin and service accounts",
            description="Block legacy basic auth for automation service accounts and admin workflows.",
            affected_scope="All users in the production tenant including Global administrators.",
            rollback_plan="TBD",
            maintenance_window=False,
        )
    )

    assert result.score == 100
    assert result.raw_score > result.score
    assert result.capped_score >= result.score
    assert result.level == "critical"
    assert result.recommendation == "delay_and_investigate"
    assert result.formula == FORMULA


def test_category_caps_keep_identity_scope_from_double_counting():
    result = RiskEngine().analyze(
        make_change(
            title="Global admin and break-glass MFA rollout for all users",
            description="Policy affects privileged administrator and emergency access accounts.",
            affected_scope="All users, Global administrators, break-glass emergency access accounts.",
        )
    )

    identity_scope = result.category_scores["identity_scope"]
    assert identity_scope["raw"] > identity_scope["cap"]
    assert identity_scope["capped"] == 30
    assert {"privileged_accounts_affected", "break_glass_accounts_affected", "broad_scope"}.issubset(
        {factor.code for factor in result.risk_factors}
    )


def test_demo_asset_context_detects_mvp_scenario_risks():
    change = make_change(
        title="Enable MFA for all contractors",
        description="Require MFA for all external contractor accounts and block legacy authentication.",
        environment=Environment.entra_id,
        change_type=ChangeType.mfa_rollout,
        affected_scope="All contractor accounts, VPN access, Microsoft 365, legacy business applications.",
        rollback_plan="Disable the new Conditional Access policy.",
        maintenance_window=False,
        pilot_enabled=False,
        report_only_mode=False,
    )
    histories = [
        make_historical(
            title="MFA enforcement for all contractors",
            description="Contractor MFA enforcement broke shared vendor accounts and badge provisioning.",
            environment=Environment.entra_id,
            change_type=ChangeType.mfa_rollout,
            root_cause="missing_exception",
            downtime_minutes=95,
        ),
        make_historical(
            title="MFA enforcement for emergency access accounts",
            description="Emergency access accounts were included in MFA enforcement by mistake.",
            environment=Environment.entra_id,
            change_type=ChangeType.mfa_rollout,
            root_cause="break_glass_account_impact",
            downtime_minutes=40,
        ),
    ]

    result = RiskEngine().analyze(
        change,
        histories,
        asset_context=get_demo_asset_context(change),
    )
    factor_codes = {factor.code for factor in result.risk_factors}

    assert result.level == "critical"
    assert result.recommendation == "delay_and_investigate"
    assert len(result.risk_factors) >= 5
    assert len(result.checklist_items) >= 6
    assert {
        "broad_scope",
        "legacy_applications_present",
        "service_accounts_affected",
        "break_glass_accounts_affected",
        "pilot_missing",
        "report_only_missing",
        "weak_rollback_validation",
        "similar_failures_found",
    }.issubset(factor_codes)
