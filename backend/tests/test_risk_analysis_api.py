from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.change import RiskAssessment, RiskFactor


def high_risk_change_payload() -> dict:
    return {
        "title": "Tenant-wide legacy authentication block for administrators",
        "description": (
            "Block legacy basic auth for automation service accounts, app registrations, "
            "and administrator workflows."
        ),
        "environment": "microsoft_365",
        "change_type": "legacy_authentication_block",
        "planned_start": datetime(2026, 8, 2, 10, 0, tzinfo=UTC).isoformat(),
        "planned_end": datetime(2026, 8, 2, 11, 0, tzinfo=UTC).isoformat(),
        "affected_scope": "All users in the production tenant including Global administrators.",
        "rollback_plan": "TBD",
        "maintenance_window": False,
        "pilot_enabled": False,
        "report_only_mode": False,
    }


def mfa_contractors_payload() -> dict:
    return {
        "title": "Enable MFA for all contractors",
        "description": "Require MFA for all external contractor accounts and block legacy authentication.",
        "environment": "entra_id",
        "change_type": "mfa_rollout",
        "planned_start": datetime(2026, 8, 5, 10, 0, tzinfo=UTC).isoformat(),
        "planned_end": datetime(2026, 8, 5, 11, 0, tzinfo=UTC).isoformat(),
        "affected_scope": "All contractor accounts, VPN access, Microsoft 365, legacy business applications.",
        "rollback_plan": "Disable the new Conditional Access policy.",
        "maintenance_window": False,
        "pilot_enabled": False,
        "report_only_mode": False,
    }


def test_get_similar_changes_returns_ranked_matches(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()

    seed_response = client.post("/api/v1/demo/seed")
    assert seed_response.status_code == 200

    create_response = client.post("/api/v1/changes", json=mfa_contractors_payload())
    assert create_response.status_code == 201
    change_id = create_response.json()["id"]

    response = client.get(f"/api/v1/changes/{change_id}/similar?limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert payload[0]["historical_change_id"] == "00000000-0000-4000-8000-000000000002"
    assert payload[0]["outcome"] == "failed"
    assert payload[0]["incident_occurred"] is True
    assert payload[0]["similarity_score"] >= payload[1]["similarity_score"]
    assert payload[0]["matching_factors"]


def test_analyze_change_creates_and_replaces_assessment(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()

    seed_response = client.post("/api/v1/demo/seed")
    assert seed_response.status_code == 200

    create_response = client.post("/api/v1/changes", json=high_risk_change_payload())
    assert create_response.status_code == 201
    change_id = create_response.json()["id"]

    first_analysis = client.post(f"/api/v1/changes/{change_id}/analyze")
    assert first_analysis.status_code == 200
    first_payload = first_analysis.json()

    assert first_payload["score"] == 100
    assert first_payload["level"] == "critical"
    assert first_payload["recommendation"] == "delay_and_investigate"
    assert first_payload["formula"] == "score = min(100, sum(min(category_cap, max(0, sum(points by category)))))"
    assert first_payload["raw_score"] >= first_payload["score"]
    assert first_payload["capped_score"] >= first_payload["score"]
    assert first_payload["category_scores"]["identity_scope"]["cap"] == 30

    factor_codes = {factor["code"] for factor in first_payload["risk_factors"]}
    assert {
        "privileged_accounts_affected",
        "service_accounts_affected",
        "rollback_plan_missing",
        "broad_scope",
        "legacy_applications_present",
        "outside_maintenance_window",
        "similar_failures_found",
    }.issubset(factor_codes)
    assert first_payload["checklist_items"]

    get_response = client.get(f"/api/v1/changes/{change_id}/assessment")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == first_payload["id"]

    second_analysis = client.post(f"/api/v1/changes/{change_id}/analyze")
    assert second_analysis.status_code == 200
    second_payload = second_analysis.json()

    assert second_payload["id"] != first_payload["id"]
    assert second_payload["score"] == first_payload["score"]

    with Session(get_engine()) as db:
        assessment_count = db.scalar(
            select(func.count())
            .select_from(RiskAssessment)
            .where(RiskAssessment.change_request_id == UUID(change_id))
        )
        factor_count = db.scalar(
            select(func.count())
            .select_from(RiskFactor)
            .join(RiskAssessment)
            .where(RiskAssessment.change_request_id == UUID(change_id))
        )

    assert assessment_count == 1
    assert factor_count == len(second_payload["risk_factors"])


def test_mvp_demo_scenario_produces_expected_risk_result(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()

    seed_response = client.post("/api/v1/demo/seed")
    assert seed_response.status_code == 200

    create_response = client.post("/api/v1/changes", json=mfa_contractors_payload())
    assert create_response.status_code == 201
    change_id = create_response.json()["id"]

    analysis_response = client.post(f"/api/v1/changes/{change_id}/analyze")
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    factor_codes = {factor["code"] for factor in analysis["risk_factors"]}

    assert analysis["level"] in {"high", "critical"}
    assert analysis["recommendation"] in {"pilot_first", "delay_and_investigate"}
    assert len(analysis["risk_factors"]) >= 5
    assert len(analysis["checklist_items"]) >= 6
    assert analysis["blast_radius"]["users_count"] == 127
    assert analysis["blast_radius"]["applications_count"] == 4
    assert analysis["blast_radius"]["service_accounts_count"] == 3
    assert len(analysis["impact_paths"]) >= 4
    assert len(analysis["predicted_failure_modes"]) >= 4
    assert {"Contractor Accounts", "svc-vendor-billing", "breakglass-cloud-02"}.issubset(
        {asset["name"] for asset in analysis["directly_affected_assets"]}
    )
    assert {"Vendor Billing", "Badge Provisioning", "Remote Contractor Access"}.issubset(
        {asset["name"] for asset in analysis["affected_business_services"]}
    )
    assert any("No tested rollback evidence" in item for item in analysis["missing_context"])
    assert any(mode["code"] == "vpn_access_disruption" for mode in analysis["predicted_failure_modes"])
    assert any(mode["code"] == "break_glass_lockout" for mode in analysis["predicted_failure_modes"])
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

    similar_response = client.get(f"/api/v1/changes/{change_id}/similar?limit=5")
    assert similar_response.status_code == 200
    similar = similar_response.json()
    failed_similar = [item for item in similar if item["outcome"] == "failed" or item["incident_occurred"]]

    assert len(similar) >= 3
    assert len(failed_similar) >= 2


def test_full_demo_analysis_returns_expected_impact_paths_and_evidence(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()

    assert client.post("/api/v1/demo/seed").status_code == 200
    create_response = client.post("/api/v1/changes", json=mfa_contractors_payload())
    assert create_response.status_code == 201
    change_id = create_response.json()["id"]

    analysis_response = client.post(f"/api/v1/changes/{change_id}/analyze")
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()

    path_text = "\n".join(" -> ".join(path["path"]) for path in analysis["impact_paths"])
    assert "svc-vendor-billing -> Vendor Billing EWS Export -> Vendor Billing" in path_text
    assert "Legacy Contractor VPN -> Remote Contractor Access" in path_text
    assert analysis["category_scores"]["identity_scope"]["raw"] > analysis["category_scores"]["identity_scope"]["capped"]
    assert analysis["category_scores"]["identity_scope"]["capped"] == 30
    assert analysis["similar_changes"]
    assert analysis["similar_changes"][0]["similarity_score"] >= analysis["similar_changes"][1]["similarity_score"]


def test_get_assessment_returns_404_before_analysis(client):
    create_response = client.post("/api/v1/changes", json=high_risk_change_payload())
    assert create_response.status_code == 201
    change_id = create_response.json()["id"]

    response = client.get(f"/api/v1/changes/{change_id}/assessment")

    assert response.status_code == 404
    assert response.json()["detail"] == "Risk assessment not found"
