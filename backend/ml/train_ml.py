"""Leak-aware experimental forecasters; synthetic demo artifacts only."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.multioutput import MultiOutputRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_loader import ENVIRONMENT_COLUMNS, PREMED_COLUMNS, SYSTEM_FIELDS, VITAL_COLUMNS, build_synthetic_corpus  # noqa: E402

LOGGER = logging.getLogger("astroguard.ml.train")
MODEL_DIR = ROOT / "models"
DATA_PATH = ROOT / "data" / "processed" / "synthetic_demo_70day.csv"
LAB_FIELDS = {"wbc_count_k_ul", "nlr_ratio", "serum_calcium_mg_dl", "urinary_calcium_mg_day"}
FORECAST_FIELDS = {
    "heart": ("resting_hr_bpm",),
    "nerve": ("winscat_rt_ms",),
    "immune": ("nlr_ratio",),
    "bone": ("bmd_drift_pct",),
}


def _slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, values, 1)[0])


def _feature_window(person: pd.DataFrame, mission_day: int) -> dict[str, float]:
    baseline_rows = person[(person.mission_day >= -14) & (person.mission_day <= 0)].sort_values("mission_day")
    past = person[(person.mission_day >= 1) & (person.mission_day <= mission_day)].sort_values("mission_day")
    if baseline_rows.empty or past.empty:
        raise ValueError("Every mission window requires pre-flight baseline and current mission data")
    pad_n = max(0, 14 - len(past))
    # Padding comes only from Earth baseline days, never from future mission rows.
    padded = pd.concat([baseline_rows.tail(pad_n), past.tail(14)], ignore_index=True).tail(14)
    result: dict[str, float] = {}
    for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS:
        values = pd.to_numeric(padded[field], errors="coerce")
        # Sparse assay values are forward-filled within the available past window;
        # leading gaps use the person's Earth baseline median.
        baseline = pd.to_numeric(baseline_rows[field], errors="coerce").dropna()
        earth_mean = float(baseline.mean()) if not baseline.empty else 0.0
        earth_std = float(baseline.std(ddof=1)) if len(baseline) > 1 else 0.0
        filled = values.ffill().fillna(earth_mean).to_numpy(dtype=float)
        result[field] = float(filled[-1])
        result[f"{field}__slope3"] = _slope(filled[-3:])
        result[f"{field}__slope14"] = _slope(filled)
        result[f"{field}__std14"] = float(np.std(filled, ddof=1)) if len(filled) > 1 else 0.0
        denom = earth_mean if abs(earth_mean) > 1e-6 else 1.0
        result[f"{field}__delta_pct"] = (filled[-1] - earth_mean) / denom * 100.0
        result[f"{field}__z_drift"] = (filled[-1] - earth_mean) / max(earth_std, 1e-5)
        if field in LAB_FIELDS:
            valid_days = past.loc[pd.to_numeric(past[field], errors="coerce").notna(), "mission_day"]
            result[f"{field}__days_since_last_lab"] = float(mission_day - valid_days.max()) if not valid_days.empty else float(mission_day)
    for flag in PREMED_COLUMNS:
        result[flag] = float(person[flag].iloc[0])
    result["mission_day"] = float(mission_day)
    return result


def build_windows(data: pd.DataFrame, *, horizon: int = 7) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    features, labels, groups = [], [], []
    for astronaut_id, person in data.groupby("astronaut_id", sort=False):
        person = person.sort_values("mission_day").reset_index(drop=True)
        mission_max = int(person.loc[~person.is_baseline, "mission_day"].max())
        for day in range(1, mission_max - horizon + 1):
            features.append(_feature_window(person, day))
            future = person.set_index("mission_day")
            target: dict[str, float] = {}
            for offset in range(1, horizon + 1):
                for system, fields in SYSTEM_FIELDS.items():
                    raw = [float(future.loc[day + offset, field]) for field in fields]
                    for field, value in zip(fields, raw):
                        target[f"{field}__t+{offset}"] = value
                    future_row = future.loc[day + offset]
                    if system == "heart":
                        components = [abs(float(future_row.resting_hr_bpm) - float(future.loc[0, "resting_hr_bpm"])) / 25.0, abs(float(future_row.sbp_mmhg) - float(future.loc[0, "sbp_mmhg"])) / 30.0]
                    elif system == "nerve":
                        components = [max(0.0, 7.0 - float(future_row.sleep_duration_hrs)) / 2.5, max(0.0, float(future_row.winscat_rt_ms) - float(future.loc[0, "winscat_rt_ms"])) / 150.0]
                    elif system == "immune":
                        components = [max(0.0, float(future_row.nlr_ratio) - float(future.loc[0, "nlr_ratio"])) / 2.5, max(0.0, float(future.loc[0, "wbc_count_k_ul"]) - float(future_row.wbc_count_k_ul)) / 3.0]
                    else:
                        components = [abs(float(future_row.bmd_drift_pct)) / 2.0, max(0.0, float(future_row.urinary_calcium_mg_day) - 250.0) / 350.0]
                    target[f"{system}_demo_risk__t+{offset}"] = float(np.clip(max(components), 0.0, 1.0))
            labels.append(target)
            groups.append(astronaut_id)
    return pd.DataFrame(features).replace([np.inf, -np.inf], np.nan).fillna(0), pd.DataFrame(labels), pd.Series(groups, name="astronaut_id")


def _model() -> MultiOutputRegressor:
    base = LGBMRegressor(
        n_estimators=2, learning_rate=0.08, num_leaves=5, max_depth=3,
        min_child_samples=12, reg_lambda=1.0, verbosity=-1, n_jobs=1,
        random_state=2026,
    )
    return MultiOutputRegressor(base, n_jobs=1)


def detect_sudden_changes(artifact: dict[str, Any], current: dict[str, float], previous: dict[str, float] | None = None) -> dict[str, Any]:
    """IsolationForest context plus explicit demo triggers; no medical diagnosis."""
    columns = artifact["feature_columns"]
    vector = pd.DataFrame([[float(current.get(name, 0.0)) for name in columns]], columns=columns)
    anomaly = int(artifact["estimator"].predict(vector)[0]) == -1
    triggers = []
    if previous:
        if "sbp_mmhg" in current and "sbp_mmhg" in previous and previous["sbp_mmhg"] - current["sbp_mmhg"] > 15:
            triggers.append("demo_sbp_drop_gt_15_mmhg")
        if "daily_rad_rate_msv" in current and current["daily_rad_rate_msv"] > 5:
            triggers.append("demo_daily_radiation_gt_5_msv")
    if current.get("cabin_co2_mmhg", 0) > 3.5:
        triggers.append("demo_cabin_co2_gt_3_5_mmhg")
    return {"anomaly_detected": anomaly or bool(triggers), "isolation_forest_flag": anomaly, "demo_triggers": triggers, "interpretation": "Research demo flag only; review source quality and mission procedures."}


def _validate_grouped(features: pd.DataFrame, labels: pd.DataFrame, groups: pd.Series) -> dict[str, float]:
    splitter = GroupKFold(n_splits=3)
    scores = []
    # Grouped validation uses a representative horizon target to keep CPU time
    # bounded; final artifacts still fit each system's full trajectory target set.
    target = "resting_hr_bpm__t+1"
    for train_idx, valid_idx in splitter.split(features, labels[target], groups):
        predictor = LGBMRegressor(n_estimators=2, learning_rate=0.08, num_leaves=5, max_depth=3, min_child_samples=8, verbosity=-1, n_jobs=1, random_state=2026)
        predictor.fit(features.iloc[train_idx], labels[target].iloc[train_idx])
        pred = predictor.predict(features.iloc[valid_idx])
        scores.append((mean_absolute_error(labels[target].iloc[valid_idx], pred), mean_squared_error(labels[target].iloc[valid_idx], pred) ** 0.5))
    return {"groupkfold_mae": float(np.mean([score[0] for score in scores])), "groupkfold_rmse": float(np.mean([score[1] for score in scores]))}


def forecast_trajectory(artifact: dict[str, Any], feature_row: dict[str, float]) -> dict[str, dict[str, float]]:
    """Predict the trained synthetic benchmark trajectory, grouped by horizon."""
    ordered = pd.DataFrame([[float(feature_row.get(name, 0.0)) for name in artifact["feature_columns"]]], columns=artifact["feature_columns"])
    values = artifact["model"].predict(ordered)[0]
    output: dict[str, dict[str, float]] = {}
    for name, value in zip(artifact["target_columns"], values):
        target, horizon = name.rsplit("__t+", 1)
        output.setdefault(f"day_{horizon}", {})[target] = float(value)
    return output


def train_all(data: pd.DataFrame | None = None) -> dict[str, Path]:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if data is None:
        data = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else build_synthetic_corpus()
    if data["astronaut_id"].nunique() < 3:
        raise ValueError("Need at least three astronaut groups for GroupKFold validation")
    features, labels, groups = build_windows(data)
    LOGGER.info("Windows: X=%s y=%s groups=%d", features.shape, labels.shape, groups.nunique())
    metrics = _validate_grouped(features, labels, groups)
    LOGGER.info("Synthetic held-out-person metrics (not clinical performance): MAE=%.4f RMSE=%.4f", metrics["groupkfold_mae"], metrics["groupkfold_rmse"])
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for system in SYSTEM_FIELDS:
        target_names = set(FORECAST_FIELDS[system])
        columns = [column for column in labels.columns if column.startswith(tuple(f"{name}__t+" for name in target_names)) or column.startswith(f"{system}_demo_risk")]
        estimator = _model().fit(features, labels[columns])
        path = MODEL_DIR / f"{system if system != 'nerve' else 'nerve'}_model.pkl"
        joblib.dump({"model": estimator, "feature_columns": list(features.columns), "target_columns": columns, "data_origin": "synthetic_demo_only", "clinical_use": False}, path)
        paths[system] = path
        LOGGER.info("Saved %s", path)
    detector_columns = ["resting_hr_bpm", "sbp_mmhg", "cabin_co2_mmhg", "daily_rad_rate_msv", "nlr_ratio", "bmd_drift_pct"]
    detector = IsolationForest(n_estimators=80, contamination=0.03, random_state=2026, n_jobs=1).fit(features[detector_columns])
    anomaly_path = MODEL_DIR / "anomaly_detector.pkl"
    joblib.dump({"estimator": detector, "feature_columns": detector_columns, "data_origin": "synthetic_demo_only", "clinical_use": False}, anomaly_path)
    paths["anomaly"] = anomaly_path
    joblib.dump({"metrics": metrics, "data_origin": "synthetic_demo_only", "clinical_use": False}, MODEL_DIR / "training_metrics.pkl")
    return paths


def explain_and_recommend(window_features: dict[str, float], models: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return model drivers and scenario comparisons for clinician review.

    Counterfactual deltas are toy scenario effects, not treatment advice or a
    claim that a countermeasure is appropriate for a particular crewmember.
    """
    if models is None:
        models = {}
        for name in ("heart", "nerve", "immune", "bone"):
            path = MODEL_DIR / f"{name}_model.pkl"
            if path.exists():
                models[name] = joblib.load(path)
    # Rank observed z-drift values by mean fitted LightGBM gain importance.
    # This is feature-importance attribution, not a causal explanation.
    importance: dict[str, float] = {}
    for artifact in models.values():
        estimator = artifact.get("model") if isinstance(artifact, dict) else None
        fitted = getattr(estimator, "estimators_", [])
        if not fitted:
            continue
        names = artifact.get("feature_columns", [])
        gains = np.mean([model.feature_importances_ for model in fitted], axis=0)
        for name, gain in zip(names, gains):
            importance[name] = max(importance.get(name, 0.0), float(gain))
    candidates = {
        key: abs(float(value)) * (importance.get(key, 1.0) if importance else 1.0)
        for key, value in window_features.items()
        if key.endswith("__z_drift") and np.isfinite(value)
    }
    driver = max(candidates, key=candidates.get) if candidates else "insufficient_feature_evidence"
    scenarios = ["electrolyte_fluid_loading", "LBNP", "ECLSS_CO2_scrubber_boost", "circadian_light_therapy", "ARED_exercise_plus_15pct", "storm_shelter_relocation"]
    # Deltas are explicitly artificial, deterministic demo comparisons.
    impact = {
        "ECLSS_CO2_scrubber_boost": max(0.0, float(window_features.get("cabin_co2_mmhg", 0)) - 2.0) * 0.08,
        "circadian_light_therapy": max(0.0, 7.0 - float(window_features.get("sleep_duration_hrs", 7))) * 0.04,
        "ARED_exercise_plus_15pct": max(0.0, 85.0 - float(window_features.get("ared_exercise_load_pct", 85))) * 0.002,
        "electrolyte_fluid_loading": 0.0, "LBNP": 0.0, "storm_shelter_relocation": 0.0,
    }
    ranked = sorted(scenarios, key=lambda action: impact[action], reverse=True)
    return {"primary_observed_driver": driver, "ranked_scenarios_for_clinician_review": [{"scenario": action, "synthetic_demo_delta": round(impact[action], 4)} for action in ranked], "scenario_note": "Illustrative counterfactual only; not an intervention recommendation or risk probability.", "model_artifact_count": len(models)}


if __name__ == "__main__":
    paths = train_all()
    for name, path in paths.items():
        print(f"{name}: {path}")
