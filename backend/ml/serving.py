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
    training_metrics: dict[str, Any] | None = None
    metrics_path = model_dir / "training_metrics.pkl"
    try:
        metrics_artifact = joblib.load(metrics_path)
        if isinstance(metrics_artifact, dict) and metrics_artifact.get("data_origin") == "synthetic_demo_only":
            training_metrics = metrics_artifact.get("metrics")
    except FileNotFoundError:
        pass
    except Exception:
        # Metrics are informational only; a broken metrics file should not
        # prevent model inference from starting.
        training_metrics = None
    return {
        "models": models,
        "status": statuses,
        "feature_names": feature_names,
        "all_loaded": len(models) == len(MODEL_FILES),
        "data_origin": "synthetic_demo_only",
        "clinical_use": False,
        "training_metrics": training_metrics,
    }


def _normalized_row(
    observation: dict[str, Any],
    defaults: dict[str, float],
    *,
    preserve_missing: bool = False,
) -> dict[str, float]:
    result = dict(defaults)
    for key in VITAL_COLUMNS + ENVIRONMENT_COLUMNS:
        value = observation.get(key)
        if value is not None:
            result[key] = float(value)
        elif preserve_missing:
            result[key] = float("nan")
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
    earth_rows = [_normalized_row(item, EARTH_DEFAULTS, preserve_missing=True) for item in earth_observations]
    earth_mean: dict[str, float] = {}
    for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS:
        observed = [row[field] for row in earth_rows if np.isfinite(row[field])]
        earth_mean[field] = float(np.mean(observed)) if observed else EARTH_DEFAULTS[field]
    for index, values in enumerate(earth_rows):
        # Earth defaults are feature imputations only; data_quality below
        # reports which values were actually supplied.
        filled = {field: values[field] if np.isfinite(values[field]) else earth_mean[field] for field in values}
        rows.append({"astronaut_id": "REQUEST", "mission_day": index - len(earth_rows), "is_baseline": True, "data_origin": "request_demo", **filled, **premedical})
    rows.append({"astronaut_id": "REQUEST", "mission_day": 0, "is_baseline": True, "data_origin": "request_demo", **earth_mean, **premedical})

    cumulative = 0.0
    current_values: dict[str, float] = {}
    prior_values: dict[str, float] = dict(earth_mean)
    mission_day = int(request_data.get("mission_day") or len(mission_observations))
    first_day = mission_day - len(mission_observations) + 1
    environment_defaults = {key: MISSION_DEFAULTS[key] for key in ENVIRONMENT_COLUMNS}
    mission_defaults = {**earth_mean, **environment_defaults}
    for day, observation in enumerate(mission_observations, start=first_day):
        values = _normalized_row(observation, mission_defaults, preserve_missing=True)
        # Use an explicit engineering default for absent cabin fields in the
        # model feature vector, while keeping them absent from detector input.
        model_values = dict(values)
        for field in ENVIRONMENT_COLUMNS:
            if not np.isfinite(model_values[field]):
                model_values[field] = MISSION_DEFAULTS[field]
        if observation.get("cumulative_rad_msv") is None:
            rate = values["daily_rad_rate_msv"]
            if np.isfinite(rate):
                cumulative += rate
                values["cumulative_rad_msv"] = cumulative
                model_values["cumulative_rad_msv"] = cumulative
            else:
                values["cumulative_rad_msv"] = float("nan")
                model_values["cumulative_rad_msv"] = float("nan")
        else:
            cumulative = values["cumulative_rad_msv"]
        rows.append({"astronaut_id": "REQUEST", "mission_day": day, "is_baseline": False, "data_origin": "request_demo", **model_values, **premedical})
        prior_values = current_values or dict(earth_mean)
        current_values = {
            field: float(values[field])
            for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS
            if np.isfinite(values[field]) and observation.get(field) is not None
        }
        if observation.get("cumulative_rad_msv") is not None and np.isfinite(values["cumulative_rad_msv"]):
            current_values["cumulative_rad_msv"] = float(values["cumulative_rad_msv"])

    person = pd.DataFrame(rows).sort_values("mission_day").reset_index(drop=True)
    current_day = mission_day
    features = _feature_window(person, current_day)
    return features, current_values, prior_values, current_day


def input_quality(request_data: dict[str, Any]) -> dict[str, Any]:
    """Describe supplied values separately from values imputed for inference."""
    fields = VITAL_COLUMNS + ENVIRONMENT_COLUMNS
    baseline = request_data.get("earth_baseline", [])
    mission = request_data.get("mission_telemetry", [])[-14:]
    latest = mission[-1] if mission else {}

    def has_value(point: dict[str, Any], field: str) -> bool:
        if point.get(field) is not None:
            return True
        return field == "pulse_pressure_mmhg" and point.get("sbp_mmhg") is not None and point.get("dbp_mmhg") is not None

    latest_missing = [field for field in fields if not has_value(latest, field)]
    baseline_missing = [field for field in fields if not any(has_value(point, field) for point in baseline)]
    system_fields = {
        "heart": SYSTEM_FIELDS["heart"],
        "nervous_system": SYSTEM_FIELDS["nerve"],
        "radiation_immune": SYSTEM_FIELDS["immune"],
        "bone_loss": SYSTEM_FIELDS["bone"],
    }
    system_coverage = {}
    for system, required in system_fields.items():
        observed = [field for field in required if any(has_value(point, field) for point in mission)]
        system_coverage[system] = {
            "observed_fields": observed,
            "missing_fields": [field for field in required if field not in observed],
            "coverage_pct": round(len(observed) / len(required) * 100.0, 1),
        }
    return {
        "latest_observed_field_count": len(fields) - len(latest_missing),
        "expected_field_count": len(fields),
        "latest_missing_fields": latest_missing,
        "baseline_missing_fields": baseline_missing,
        "system_coverage": system_coverage,
        "imputation_policy": "Earth baseline and documented demo cabin defaults may fill model features; absent measurements are listed and are not treated as observed alerts.",
    }


def run_forecast(request_data: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    features, current, prior, mission_day = build_live_window(request_data)
    models = registry.get("models", {})
    anomaly = models.get("anomaly")
    detector_result = detect_sudden_changes(anomaly, current, prior) if anomaly else {"anomaly_detected": False, "demo_triggers": [], "isolation_forest_flag": None, "interpretation": "Anomaly artifact unavailable."}
    alerts = []
    for trigger in detector_result.get("demo_triggers", []):
        sensor, relation, threshold, unit = TRIGGER_DETAILS.get(trigger, ("unknown", "triggered", None, ""))
        alerts.append({"sensor": sensor, "trigger": trigger, "relation": relation, "threshold": threshold, "unit": unit, "observed_value": current.get(sensor), "basis": "demo heuristic only"})
    if detector_result.get("isolation_forest_flag") is True:
        alerts.append({"sensor": "multi_sensor_vector", "trigger": "isolation_forest_outlier", "basis": "synthetic training distribution; review manually"})

    quality = input_quality(request_data)
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
        systems[system_key] = {
            "available": True,
            "trajectory": series,
            "primary_driver": explanation["primary_observed_driver"],
            "recommended_action": "qualified_clinician_review",
            "scenario_candidate_for_review": None,
            "projected_risk_reduction_pct": None,
            "input_coverage_pct": quality["system_coverage"][system_key]["coverage_pct"],
            "score_note": "Synthetic benchmark score only. No countermeasure effect or clinical risk probability is estimated.",
        }
    return {
        "mission_day": mission_day,
        "data_origin": request_data.get("data_origin", "request_demo_or_unvalidated_observation"),
        "model_origin": "synthetic_demo_only",
        "sudden_drop_detected": bool(detector_result.get("anomaly_detected")),
        "acute_alerts": alerts,
        "systems": systems,
        "data_quality": quality,
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
        "training_metrics": registry.get("training_metrics"),
        "data_origin": "synthetic_demo_only",
        "clinical_use": False,
        "limitations": ["Training targets are synthetic; OSDR/NLSP files are cached but not harmonized into labels.", "Outputs are research demo values, not calibrated medical predictions."],
    }
