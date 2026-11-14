def test_measurement_analysis_and_medical_review_workflow(client):
    astronaut_id = client.astronaut_id

    profile = client.get(f"/api/v1/astronauts/{astronaut_id}")
    assert profile.status_code == 200
    assert profile.json()["callsign"] == "TEST"

    measurement = client.post(
        f"/api/v1/astronauts/{astronaut_id}/measurements",
        json={"metric": "heart_rate", "value": 110, "unit": "bpm", "source_type": "manual"},
    )
    assert measurement.status_code == 201
    assert measurement.json()["source_type"] == "manual"

    analysis = client.post(f"/api/v1/astronauts/{astronaut_id}/analysis")
    assert analysis.status_code == 200
    assert analysis.json()["needs_review"] is True
    assert analysis.json()["findings"][0]["is_flagged"] is True

    alerts = client.get(f"/api/v1/astronauts/{astronaut_id}/alerts")
    assert alerts.status_code == 200
    alert = next(item for item in alerts.json() if item["measurement_id"] == measurement.json()["id"])
    assert alert["status"] == "open"

    updated = client.patch(
        f"/api/v1/alerts/{alert['id']}",
        json={"status": "acknowledged", "reviewer_notes": "Reviewed source record.", "reviewed_by": "Dr. Test"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "acknowledged"
    assert updated.json()["reviewer_notes"] == "Reviewed source record."

    resolved = client.patch(f"/api/v1/alerts/{alert['id']}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_profile_and_medical_history_crud(client):
    astronaut_id = client.astronaut_id
    created = client.post(
        f"/api/v1/astronauts/{astronaut_id}/medical-history",
        json={"category": "Review note", "summary": "Test-only history entry.", "recorded_by": "Test reviewer"},
    )
    assert created.status_code == 201
    history_id = created.json()["id"]
    assert client.get(f"/api/v1/astronauts/{astronaut_id}/medical-history").json()[0]["summary"] == "Test-only history entry."

    patched = client.patch(f"/api/v1/medical-history/{history_id}", json={"summary": "Updated note."})
    assert patched.status_code == 200
    assert patched.json()["summary"] == "Updated note."

    deleted = client.delete(f"/api/v1/medical-history/{history_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/astronauts/{astronaut_id}/medical-history").json() == []


def test_mission_and_astronaut_creation(client):
    mission = client.post("/api/v1/missions", json={"name": "Second mission", "destination": "Lunar orbit"})
    assert mission.status_code == 201
    created = client.post("/api/v1/astronauts", json={
        "mission_id": mission.json()["id"], "full_name": "New Crew", "callsign": "CREW-2", "role": "Specialist",
    })
    assert created.status_code == 201
    assert created.json()["mission"]["name"] == "Second mission"
    assert client.get("/api/v1/astronauts", params={"q": "CREW-2"}).json()[0]["callsign"] == "CREW-2"


def test_invalid_alert_id_is_rejected(client):
    response = client.patch("/api/v1/alerts/not-a-uuid", json={"status": "ignored"})
    assert response.status_code == 422


def test_unsupported_measurement_metric_is_rejected(client):
    response = client.post(
        f"/api/v1/astronauts/{client.astronaut_id}/measurements",
        json={"metric": "made_up_signal", "value": 1, "unit": "unit"},
    )
    assert response.status_code == 422


def test_unconnected_nasa_source_cannot_be_claimed(client):
    response = client.post(
        f"/api/v1/astronauts/{client.astronaut_id}/measurements",
        json={"metric": "heart_rate", "value": 70, "unit": "bpm", "source_type": "nasa"},
    )
    assert response.status_code == 422
