"""Safe loading and request-time adapters for the isolated ML demo artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml.data_loader import ENVIRONMENT_COLUMNS, PREMED_COLUMNS, SYSTEM_FIELDS, VITAL_COLUMNS
from ml.train_ml import _feature_window, detect_sudden_changes, explain_and_recommend, forecast_trajectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = BACKEND_ROOT / "models"
MODEL_FILES = {
    "heart": "heart_model.pkl",
    "nerve": "nerve_model.pkl",
    "immune": "immune_model.pkl",
    "bone": "bone_model.pkl",
    "anomaly": "anomaly_detector.pkl",
}
SYSTEM_KEYS = {"heart": "heart", "nerve": "nervous_system", "immune": "radiation_immune", "bone": "bone_loss"}
FORECAST_METRICS = {"heart": "resting_hr_bpm", "nerve": "winscat_rt_ms", "immune": "nlr_ratio", "bone": "bmd_drift_pct"}
EARTH_DEFAULTS = {
    "resting_hr_bpm": 68.0, "hrv_rmssd_ms": 58.0, "sbp_mmhg": 116.0, "dbp_mmhg": 76.0,
    "pulse_pressure_mmhg": 40.0, "sleep_duration_hrs": 7.5, "sleep_efficiency_pct": 88.0,
    "winscat_rt_ms": 500.0, "winscat_accuracy_pct": 94.0, "cumulative_rad_msv": 0.0,
    "daily_rad_rate_msv": 0.0, "wbc_count_k_ul": 6.5, "nlr_ratio": 1.8, "bmd_drift_pct": 0.0,
    "serum_calcium_mg_dl": 9.4, "urinary_calcium_mg_day": 180.0, "ared_exercise_load_pct": 100.0,
    "gravity_g": 1.0, "cabin_co2_mmhg": 0.0, "cabin_po2_mmhg": 159.0, "cabin_pressure_psi": 14.7,
}
MISSION_DEFAULTS = {**EARTH_DEFAULTS, "gravity_g": 0.0, "cabin_co2_mmhg": 1.8, "cabin_po2_mmhg": 151.0, "cabin_pressure_psi": 14.6, "daily_rad_rate_msv": 0.65, "ared_exercise_load_pct": 90.0}
THRESHOLD_METADATA = {
    "cabin_co2_mmhg": {"demo_trigger": "> 3.5", "unit": "mmHg", "basis": "engineering demo heuristic; not a clinical limit"},
    "systolic_bp_drop": {"demo_trigger": "> 15", "unit": "mmHg versus prior point", "basis": "engineering demo heuristic; clinical context required"},
    "daily_rad_rate_msv": {"demo_trigger": "> 5", "unit": "mSv/day", "basis": "engineering demo heuristic; verify exposure basis and mission procedure"},
    "NASA_STD_3001": "Provides program requirements; it does not validate these prototype thresholds or models.",
}
TRIGGER_DETAILS = {
    "demo_cabin_co2_gt_3_5_mmhg": ("cabin_co2_mmhg", ">", 3.5, "mmHg"),
    "demo_sbp_drop_gt_15_mmhg": ("sbp_mmhg", "drop_gt", 15.0, "mmHg"),
    "demo_daily_radiation_gt_5_msv": ("daily_rad_rate_msv", ">", 5.0, "mSv/day"),
}


def load_model_registry(model_dir: Path = MODEL_DIR) -> dict[str, Any]:
    models: dict[str, Any] = {}
    statuses: dict[str, dict[str, Any]] = {}
    feature_names: list[str] = []
    for name, filename in MODEL_FILES.items():
        path = model_dir / filename
        try:
            artifact = joblib.load(path)
            if not isinstance(artifact, dict):
                raise ValueError("Unexpected model artifact format")
            if artifact.get("data_origin") != "synthetic_demo_only" or artifact.get("clinical_use") is not False:
                raise ValueError("Artifact is missing its synthetic-demo safety metadata")
            if name != "anomaly" and ("model" not in artifact or "feature_columns" not in artifact):
                raise ValueError("Forecast artifact is missing required fields")
            if name == "anomaly" and ("estimator" not in artifact or "feature_columns" not in artifact):
                raise ValueError("Anomaly artifact is missing required fields")
            models[name] = artifact
            statuses[name] = {"loaded": True, "file": filename}
            if not feature_names:
                feature_names = list(artifact["feature_columns"])
        except FileNotFoundError:
            statuses[name] = {"loaded": False, "file": filename, "reason": "artifact_missing"}
        except Exception as exc:
            statuses[name] = {"loaded": False, "file": filename, "reason": f"artifact_unavailable: {exc}"}
    return {
        "models": models,
        "status": statuses,
        "feature_names": feature_names,
        "all_loaded": len(models) == len(MODEL_FILES),
        "data_origin": "synthetic_demo_only",
        "clinical_use": False,
    }


def _normalized_row(observation: dict[str, Any], defaults: dict[str, float]) -> dict[str, float]:
    result = dict(defaults)
    for key in VITAL_COLUMNS + ENVIRONMENT_COLUMNS:
        value = observation.get(key)
        if value is not None:
            result[key] = float(value)
    if observation.get("pulse_pressure_mmhg") is None and observation.get("sbp_mmhg") is not None and observation.get("dbp_mmhg") is not None:
        result["pulse_pressure_mmhg"] = result["sbp_mmhg"] - result["dbp_mmhg"]
    return result


def build_live_window(request_data: dict[str, Any]) -> tuple[dict[str, float], dict[str, float], dict[str, float], int]:
    earth_observations = request_data["earth_baseline"]
    mission_observations = request_data["mission_telemetry"]
    premedical = request_data["pre_medical"]
    if not earth_observations or not mission_observations:
        raise ValueError("Provide at least one baseline and one mission observation")

    rows: list[dict[str, Any]] = []
    earth_rows = [_normalized_row(item, EARTH_DEFAULTS) for item in earth_observations]
    for index, values in enumerate(earth_rows):
        rows.append({"astronaut_id": "REQUEST", "mission_day": index - len(earth_rows), "is_baseline": True, "data_origin": "request_demo", **values, **premedical})
    earth_mean = {field: float(np.mean([row[field] for row in earth_rows])) for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS}
    rows.append({"astronaut_id": "REQUEST", "mission_day": 0, "is_baseline": True, "data_origin": "request_demo", **earth_mean, **premedical})

    cumulative = 0.0
    current_values: dict[str, float] = {}
    prior_values: dict[str, float] = dict(earth_mean)
    mission_day = int(request_data.get("mission_day") or len(mission_observations))
    first_day = mission_day - len(mission_observations) + 1
    environment_defaults = {key: MISSION_DEFAULTS[key] for key in ENVIRONMENT_COLUMNS}
    mission_defaults = {**earth_mean, **environment_defaults, "daily_rad_rate_msv": MISSION_DEFAULTS["daily_rad_rate_msv"], "ared_exercise_load_pct": MISSION_DEFAULTS["ared_exercise_load_pct"]}
    for day, observation in enumerate(mission_observations, start=first_day):
        values = _normalized_row(observation, mission_defaults)
        if observation.get("cumulative_rad_msv") is None:
            cumulative += values["daily_rad_rate_msv"]
            values["cumulative_rad_msv"] = cumulative
        else:
            cumulative = values["cumulative_rad_msv"]
        rows.append({"astronaut_id": "REQUEST", "mission_day": day, "is_baseline": False, "data_origin": "request_demo", **values, **premedical})
        prior_values = current_values or dict(earth_mean)
        current_values = values

    person = pd.DataFrame(rows).sort_values("mission_day").reset_index(drop=True)
    current_day = mission_day
    features = _feature_window(person, current_day)
    return features, current_values, prior_values, current_day


def run_forecast(request_data: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    features, current, prior, mission_day = build_live_window(request_data)
    models = registry.get("models", {})
    anomaly = models.get("anomaly")
    detector_result = detect_sudden_changes(anomaly, current, prior) if anomaly else {"anomaly_detected": False, "demo_triggers": [], "isolation_forest_flag": None, "interpretation": "Anomaly artifact unavailable."}
    alerts = []
    for trigger in detector_result.get("demo_triggers", []):
        sensor, relation, threshold, unit = TRIGGER_DETAILS.get(trigger, ("unknown", "triggered", None, ""))
        alerts.append({"sensor": sensor, "trigger": trigger, "relation": relation, "threshold": threshold, "unit": unit, "observed_value": current.get(sensor), "basis": "demo heuristic only"})
    if detector_result.get("isolation_forest_flag"):
        alerts.append({"sensor": "multi_sensor_vector", "trigger": "isolation_forest_outlier", "basis": "synthetic training distribution; review manually"})

    systems: dict[str, Any] = {}
    for name, system_key in SYSTEM_KEYS.items():
        artifact = models.get(name)
        if not artifact:
            systems[system_key] = {"available": False, "reason": "model_artifact_unavailable"}
            continue
        trajectory = forecast_trajectory(artifact, features)
        metric = FORECAST_METRICS[name]
        series = []
        for day_name in sorted(trajectory, key=lambda item: int(item.split("_")[1])):
            row = trajectory[day_name]
            demo_score = float(np.clip(row.get(f"{name}_demo_risk", 0.0), 0.0, 1.0))
            level = "demo_low" if demo_score < 0.33 else "demo_moderate" if demo_score < 0.66 else "demo_high"
            series.append({"day": int(day_name.split("_")[1]), "predicted_metric": metric, "predicted_value": row.get(metric), "demo_score": demo_score, "risk_level": level})
        explanation = explain_and_recommend(features, {name: artifact})
        best_scenario = explanation["ranked_scenarios_for_clinician_review"][0]
        systems[system_key] = {
            "available": True,
            "trajectory": series,
            "primary_driver": explanation["primary_observed_driver"],
            "recommended_action": "qualified_clinician_review",
            "scenario_candidate_for_review": best_scenario["scenario"],
            "projected_risk_reduction_pct": round(best_scenario["synthetic_demo_delta"] * 100, 2),
            "score_note": "Synthetic benchmark score only; not a clinical risk probability or treatment recommendation.",
        }
    return {
        "mission_day": mission_day,
        "data_origin": "request_demo_or_unvalidated_observation",
        "model_origin": "synthetic_demo_only",
        "sudden_drop_detected": bool(detector_result.get("anomaly_detected")),
        "acute_alerts": alerts,
        "systems": systems,
        "clinical_use": False,
        "review_note": "Experimental model output only. Not a diagnosis, medical clearance, clinical estimate, or countermeasure instruction; qualified flight-medical review and mission procedures govern decisions.",
    }


def model_info(registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "models": registry["status"],
        "models_loaded": [name for name, info in registry["status"].items() if info["loaded"]],
        "all_loaded": registry["all_loaded"],
        "input_feature_names": registry["feature_names"],
        "threshold_metadata": THRESHOLD_METADATA,
        "data_origin": "synthetic_demo_only",
        "clinical_use": False,
        "limitations": ["Training targets are synthetic; OSDR/NLSP files are cached but not harmonized into labels.", "Outputs are research demo values, not calibrated medical predictions."],
    }
