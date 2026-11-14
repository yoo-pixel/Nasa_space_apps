from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models import LearningSession, Measurement, MetricBaseline


def test_history_review_gates_learning_and_calendar_alone_is_not_enough(client):
    astronaut_id = client.astronaut_id
    history = client.post(f"/api/v1/astronauts/{astronaut_id}/medical-history", json={
        "category": "Medication", "summary": "Recorded medication list.", "source": "Flight medical file",
    })
    assert history.status_code == 201
    assert history.json()["verification_status"] == "unverified"
    blocked = client.post(f"/api/v1/astronauts/{astronaut_id}/learning", json={"started_by": "Dr. Test"})
    assert blocked.status_code == 409

    reviewed = client.patch(f"/api/v1/medical-history/{history.json()['id']}", json={
        "verification_status": "not_verified", "reviewed_by": "Dr. Test", "review_notes": "Source could not be confirmed.",
    })
    assert reviewed.status_code == 200
    assert reviewed.json()["reviewed_by"] == "Dr. Test"
    started = client.post(f"/api/v1/astronauts/{astronaut_id}/learning", json={"started_by": "Dr. Test"})
    assert started.status_code == 201
    assert started.json()["status"] == "collecting"
    assert started.json()["day_number"] == 1

    approval = client.post(f"/api/v1/learning/{started.json()['session_id']}/approve", json={"approved_by": "Dr. Test"})
    assert approval.status_code == 409
    assert "Calendar time alone" in approval.json()["detail"]


def test_learning_needs_observation_coverage_before_profile_can_be_approved(client):
    astronaut_id = UUID(client.astronaut_id)
    started = client.post(f"/api/v1/astronauts/{astronaut_id}/learning", json={"started_by": "Dr. Test"})
    assert started.status_code == 201
    with client.test_db_factory() as db:
        session = db.get(LearningSession, UUID(started.json()["session_id"]))
        now = datetime.now(timezone.utc)
        session.started_at = now - timedelta(days=15)
        metrics = [("heart_rate", 65.0, "bpm"), ("spo2", 97.0, "%"), ("temperature", 36.6, "°C")]
        for day in range(10):
            for metric, value, unit in metrics:
                db.add(Measurement(
                    astronaut_id=astronaut_id, metric=metric, value=value + day * 0.1, unit=unit,
                    measured_at=now - timedelta(days=day + 1), source_type="manual", symptoms=[], notes="test observation",
                ))
        db.commit()

    snapshot = client.get(f"/api/v1/astronauts/{astronaut_id}/learning").json()
    assert snapshot["status"] == "ready_for_review"
    assert snapshot["elapsed_days"] >= 14
    assert snapshot["distinct_days"] == 10
    assert snapshot["reading_count"] == 30

    approved = client.post(f"/api/v1/learning/{started.json()['session_id']}/approve", json={"approved_by": "Dr. Test"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "profile_active"
    with client.test_db_factory() as db:
        assert db.query(LearningSession).count() == 1
        assert db.query(Measurement).filter(Measurement.astronaut_id == astronaut_id).count() == 30
        learned = db.query(MetricBaseline).filter(MetricBaseline.astronaut_id == astronaut_id, MetricBaseline.metric == "heart_rate").one()
        assert "reviewer approved" in learned.method


def test_bone_and_radiation_records_keep_source_and_validate_units(client):
    astronaut_id = client.astronaut_id
    bone = client.post(f"/api/v1/astronauts/{astronaut_id}/bone-health", json={
        "assessment_type": "scan", "metric": "BMD · lumbar spine", "value": 1.03, "unit": "g/cm²",
        "source": "DXA report · test only", "source_verified": True,
    })
    assert bone.status_code == 201
    assert bone.json()["metric"] == "BMD · lumbar spine"
    assert client.get(f"/api/v1/astronauts/{astronaut_id}/bone-health").json()[0]["source_verified"] is True

    invalid = client.post(f"/api/v1/astronauts/{astronaut_id}/radiation", json={
        "dosimeter_id": "AD-TEST", "exposure_type": "effective", "value": 0.4, "unit": "mGy", "source": "test export",
    })
    assert invalid.status_code == 422
    radiation = client.post(f"/api/v1/astronauts/{astronaut_id}/radiation", json={
        "dosimeter_id": "AD-TEST", "exposure_type": "effective", "value": 0.4, "unit": "mSv",
        "measurement_basis": "cumulative", "source": "test export", "mission_phase": "transit", "shielding": "recorded configuration", "source_verified": True,
    })
    assert radiation.status_code == 201
    assert radiation.json()["unit"] == "mSv"
    assert radiation.json()["measurement_basis"] == "cumulative"
    invalid_rate_basis = client.post(f"/api/v1/astronauts/{astronaut_id}/radiation", json={
        "dosimeter_id": "AD-TEST", "exposure_type": "dose_rate", "value": 0.2, "unit": "µSv/h", "source": "test export",
    })
    assert invalid_rate_basis.status_code == 422
    rate = client.post(f"/api/v1/astronauts/{astronaut_id}/radiation", json={
        "dosimeter_id": "AD-TEST", "exposure_type": "dose_rate", "measurement_basis": "rate",
        "value": 0.2, "unit": "µSv/h", "source": "test export", "source_verified": True,
    })
    assert rate.status_code == 201
    assert rate.json()["measurement_basis"] == "rate"
    domains = {item["key"]: item for item in client.get(f"/api/v1/astronauts/{astronaut_id}/health-domains").json()}
    assert domains["bone"]["status"] == "data_available"
    assert domains["radiation"]["status"] == "data_available"
    assert domains["sleep_behavioral"]["status"] == "not_monitored"
    summary = client.get("/api/v1/dashboard/monitoring-summary").json()
    assert summary["bone_record_count"] == 1
    assert summary["radiation_record_count"] == 2
