from app.core.config import get_settings


def seed_demo_data(client, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()

    response = client.post("/api/v1/demo/seed")
    assert response.status_code == 200


def test_analytics_summary(client, monkeypatch):
    seed_demo_data(client, monkeypatch)

    response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_changes"] == 40
    assert payload["successful_changes"] == 23
    assert payload["failed_changes"] == 17
    assert payload["failure_rate"] == 42.5
    assert payload["changes_with_incidents"] == 17
    assert payload["average_downtime_minutes"] == 49.38
    assert payload["most_common_root_cause"] == "insufficient_testing"
    assert payload["highest_risk_change_type"] == "legacy_authentication_block"
    assert payload["common_process_failures"]
    assert payload["common_preventive_controls"]
    assert payload["common_business_impacts"]


def test_root_cause_analytics(client, monkeypatch):
    seed_demo_data(client, monkeypatch)

    response = client.get("/api/v1/analytics/root-causes")

    assert response.status_code == 200
    payload = response.json()
    missing_exception = next(item for item in payload if item["root_cause"] == "missing_exception")
    assert missing_exception["count"] == 2
    assert missing_exception["percentage"] == 11.76
    assert missing_exception["average_downtime"] == 167.5
    assert missing_exception["rollback_rate"] == 50.0
    assert missing_exception["affected_change_types"] == ["guest_access_change", "mfa_rollout"]


def test_change_type_analytics(client, monkeypatch):
    seed_demo_data(client, monkeypatch)

    response = client.get("/api/v1/analytics/change-types")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["change_type"] == "legacy_authentication_block"
    assert payload[0]["total"] == 5
    assert payload[0]["successful"] == 2
    assert payload[0]["failed"] == 3
    assert payload[0]["failure_rate"] == 60.0
    assert payload[0]["average_downtime"] == 98.0
    assert payload[0]["common_root_causes"] == [
        "documentation_gap",
        "legacy_application_dependency",
        "unknown_dependency",
    ]


def test_failure_patterns_detect_repeated_and_high_risk_groups(client, monkeypatch):
    seed_demo_data(client, monkeypatch)

    response = client.get("/api/v1/analytics/failure-patterns")

    assert response.status_code == 200
    payload = response.json()
    pattern_keys = {(item["pattern_type"], item["title"]) for item in payload}
    assert (
        "high_failure_rate_change_type",
        "High failure rate: legacy_authentication_block",
    ) in pattern_keys
    assert (
        "repeated_error_cluster",
        "At least three failures: legacy_authentication_block",
    ) in pattern_keys
    assert any(item["pattern_type"] == "high_downtime_change_type" for item in payload)
    assert any(item["pattern_type"] == "frequent_rollback_change_type" for item in payload)
    assert any(item["pattern_type"] == "repeated_causal_chain" for item in payload)
    assert len(payload) >= 5


def test_analytics_filters_by_environment_and_change_type(client, monkeypatch):
    seed_demo_data(client, monkeypatch)

    summary = client.get("/api/v1/analytics/summary?change_type=mfa_rollout")
    assert summary.status_code == 200
    assert summary.json()["total_changes"] == 5
    assert summary.json()["failed_changes"] == 2
    assert summary.json()["failure_rate"] == 40.0
    assert summary.json()["highest_risk_change_type"] == "mfa_rollout"

    root_causes = client.get("/api/v1/analytics/root-causes?environment=defender")
    assert root_causes.status_code == 200
    assert {item["root_cause"] for item in root_causes.json()} == {
        "insufficient_testing",
        "unknown_dependency",
    }

    change_types = client.get("/api/v1/analytics/change-types?environment=defender")
    assert change_types.status_code == 200
    assert [item["change_type"] for item in change_types.json()] == ["defender_policy_change"]
