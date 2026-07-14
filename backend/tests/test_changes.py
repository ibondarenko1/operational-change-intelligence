from datetime import UTC, datetime


def change_payload() -> dict:
    return {
        "title": "Conditional access rollout",
        "description": "Enable a new conditional access policy for admin users.",
        "environment": "entra_id",
        "change_type": "conditional_access",
        "planned_start": datetime(2026, 8, 1, 10, 0, tzinfo=UTC).isoformat(),
        "planned_end": datetime(2026, 8, 1, 11, 0, tzinfo=UTC).isoformat(),
        "affected_scope": "Global administrators and privileged role administrators",
        "rollback_plan": "Disable the new policy and restore previous assignment group.",
        "maintenance_window": True,
        "pilot_enabled": True,
        "report_only_mode": True,
    }


def test_change_request_crud(client):
    create_response = client.post("/api/v1/changes", json=change_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "Conditional access rollout"
    assert created["status"] == "draft"
    assert created["environment"] == "entra_id"

    change_id = created["id"]

    list_response = client.get("/api/v1/changes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/v1/changes/{change_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == change_id

    patch_response = client.patch(
        f"/api/v1/changes/{change_id}",
        json={"status": "review_required", "title": "Reviewed CA rollout"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["status"] == "review_required"
    assert patched["title"] == "Reviewed CA rollout"

    delete_response = client.delete(f"/api/v1/changes/{change_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/changes/{change_id}")
    assert missing_response.status_code == 404


def test_create_rejects_planned_end_before_start(client):
    payload = change_payload()
    payload["planned_end"] = datetime(2026, 8, 1, 9, 0, tzinfo=UTC).isoformat()

    response = client.post("/api/v1/changes", json=payload)

    assert response.status_code == 422
    assert "planned_end cannot be earlier than planned_start" in response.text


def test_patch_rejects_planned_end_before_existing_start(client):
    create_response = client.post("/api/v1/changes", json=change_payload())
    assert create_response.status_code == 201
    change_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/changes/{change_id}",
        json={"planned_end": datetime(2026, 8, 1, 9, 0, tzinfo=UTC).isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "planned_end cannot be earlier than planned_start"


def test_rejects_invalid_enum_values(client):
    payload = change_payload()
    payload["environment"] = "exchange_online"

    response = client.post("/api/v1/changes", json=payload)

    assert response.status_code == 422
