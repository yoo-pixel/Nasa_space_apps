from __future__ import annotations

from fastapi.testclient import TestClient


def _baseline() -> list[dict[str, float]]:
    points = []
    for day in range(14):
        points.append({
            "resting_hr_bpm": 68.0 + (day % 3 - 1), "hrv_rmssd_ms": 58.0,
            "sbp_mmhg": 116.0, "dbp_mmhg": 76.0, "sleep_duration_hrs": 7.5,
            "sleep_efficiency_pct": 88.0, "winscat_rt_ms": 500.0,
            "winscat_accuracy_pct": 94.0, "cumulative_rad_msv": 0.0,
            "daily_rad_rate_msv": 0.0, "wbc_count_k_ul": 6.5, "nlr_ratio": 1.8,
            "bmd_drift_pct": 0.0, "serum_calcium_mg_dl": 9.4,
            "urinary_calcium_mg_day": 180.0, "ared_exercise_load_pct": 100.0,
            "gravity_g": 1.0, "cabin_co2_mmhg": 0.0, "cabin_po2_mmhg": 159.0,
            "cabin_pressure_psi": 14.7,
        })
    return points


def _mission_point(day: int, *, co2: float = 2.0, sbp: float = 115.0) -> dict[str, float]:
    return {
        "resting_hr_bpm": 72.0, "hrv_rmssd_ms": 52.0, "sbp_mmhg": sbp,
        "dbp_mmhg": 74.0, "sleep_duration_hrs": 7.1, "sleep_efficiency_pct": 84.0,
        "winscat_rt_ms": 520.0 + day, "winscat_accuracy_pct": 92.0,
        "daily_rad_rate_msv": 0.7, "wbc_count_k_ul": 6.0, "nlr_ratio": 2.0,
        "bmd_drift_pct": -0.2, "serum_calcium_mg_dl": 9.5,
        "urinary_calcium_mg_day": 190.0, "ared_exercise_load_pct": 88.0,
        "gravity_g": 0.0, "cabin_co2_mmhg": co2, "cabin_po2_mmhg": 151.0,
        "cabin_pressure_psi": 14.6,
    }


def _payload(days: int) -> dict:
    return {
        "astronaut_id": "SIM-API-1",
        "earth_baseline": _baseline(),
        "mission_telemetry": [_mission_point(day) for day in range(1, days + 1)],
        "mission_day": days,
        "pre_medical": {"prior_arrhythmia_flag": False, "vo2_max_earth": 48, "baseline_t_score": 0.1, "baseline_optic_nerve_mm": 3.0},
    }


def test_ml_forecast_day_3_cold_start(client: TestClient) -> None:
    response = client.post("/api/v1/ml/forecast", json=_payload(3))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mission_day"] == 3
    assert body["clinical_use"] is False
    assert set(body["systems"]) == {"heart", "nervous_system", "radiation_immune", "bone_loss"}
    assert len(body["systems"]["heart"]["trajectory"]) == 7


def test_ml_forecast_day_14_flags_cabin_co2_and_sbp_drop(client: TestClient) -> None:
    payload = _payload(14)
    payload["mission_telemetry"][-2] = _mission_point(13, co2=2.0, sbp=116.0)
    payload["mission_telemetry"][-1] = _mission_point(14, co2=3.9, sbp=95.0)
    response = client.post("/api/v1/ml/forecast", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sudden_drop_detected"] is True
    triggers = {item["trigger"] for item in body["acute_alerts"]}
    assert "demo_cabin_co2_gt_3_5_mmhg" in triggers
    assert "demo_sbp_drop_gt_15_mmhg" in triggers
    alerts = {item["sensor"]: item for item in body["acute_alerts"]}
    assert alerts["cabin_co2_mmhg"]["threshold"] == 3.5
    assert alerts["sbp_mmhg"]["threshold"] == 15.0


def test_ml_demo_mission_has_30_days_and_scenario_events(client: TestClient) -> None:
    response = client.get("/api/v1/ml/demo-mission")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["timeline"]) == 30
    assert body["timeline"][11]["telemetry"]["cabin_co2_mmhg"] > 3.5
    assert body["timeline"][21]["telemetry"]["ared_exercise_load_pct"] < 40


def test_ml_model_info_reports_loaded_artifacts(client: TestClient) -> None:
    response = client.get("/api/v1/ml/model-info")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["all_loaded"] is True
    assert len(body["models_loaded"]) == 5
    assert "resting_hr_bpm__z_drift" in body["input_feature_names"]


def test_existing_health_route_adds_model_status(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert len(body["models_loaded"]) == 5

