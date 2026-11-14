"""Normalize the repository's long-form demo measurements for the ML API.

This adapter is deliberately limited to the versioned, simulated dataset in
``data/synthetic``. OSDR/NLSP exports remain raw research inputs until a
study-specific, reviewed mapper is available; their columns are not guessed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.data_loader import ENVIRONMENT_COLUMNS, VITAL_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SOURCE_MEASUREMENTS = PROJECT_ROOT / "data" / "synthetic" / "measurements.csv"
NORMALIZED_OUTPUT = BACKEND_ROOT / "data" / "processed" / "normalized_demo_measurements.csv"

REQUIRED_SOURCE_COLUMNS = {
    "astronaut_id", "timestamp", "mission_day", "variable", "value", "unit",
    "source", "quality", "is_simulated",
}

UNIT_MAP: dict[str, tuple[str, set[str]]] = {
    "heart_rate": ("resting_hr_bpm", {"bpm"}),
    "bp_systolic": ("sbp_mmhg", {"mmhg"}),
    "bp_diastolic": ("dbp_mmhg", {"mmhg"}),
    "sleep_total_h": ("sleep_duration_hrs", {"h"}),
    "sleep_time_in_bed_h": ("sleep_time_in_bed_h", {"h"}),
    "wbc": ("wbc_count_k_ul", {"10^9/l", "10⁹/l", "k/µl", "k/ul"}),
    "radiation_dose_equivalent": ("daily_rad_rate_msv", {"msv/day"}),
    "bone_density": ("__bone_density_g_cm2", {"g/cm2", "g/cm²"}),
}


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def normalize_measurements(path: Path = SOURCE_MEASUREMENTS) -> pd.DataFrame:
    """Convert known long-form variables to daily rows without fabricating data."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Demo measurement file not found: {path}")
    source = pd.read_csv(path)
    missing = REQUIRED_SOURCE_COLUMNS.difference(source.columns)
    if missing:
        raise ValueError(f"Measurement file is missing required columns: {sorted(missing)}")
    if source.empty:
        raise ValueError("Measurement file contains no records")

    source["astronaut_id"] = source["astronaut_id"].astype(str).str.strip()
    source["timestamp"] = pd.to_datetime(source["timestamp"], errors="coerce", utc=True)
    source["mission_day"] = pd.to_numeric(source["mission_day"], errors="coerce")
    source["value"] = pd.to_numeric(source["value"], errors="coerce")
    source["variable"] = source["variable"].astype(str).str.strip()
    source["unit_normalized"] = source["unit"].astype(str).str.strip().str.lower()
    source["quality_normalized"] = source["quality"].astype(str).str.strip().str.lower()
    source["is_simulated_normalized"] = source["is_simulated"].map(_is_true)
    if not source["is_simulated_normalized"].all():
        raise ValueError("This local demo adapter accepts only explicitly simulated records")

    source = source[
        source["timestamp"].notna()
        & source["mission_day"].notna()
        & source["value"].notna()
        & np.isfinite(source["value"])
        & source["quality_normalized"].isin({"good", "fair"})
    ].copy()
    source["mission_day"] = source["mission_day"].astype(int)
    # Keep the daily mission study window in this table; remote historical
    # records (for example a DXA from a year earlier) remain in the raw source
    # and are not mixed into daily telemetry rows.
    source = source[source["mission_day"] >= -29].copy()

    # Heart rate is summarized at rest only when the generator supplied an
    # activity annotation for that timestamp. Pre-flight clinic readings have
    # no activity annotation and remain eligible.
    activity = source[source["variable"] == "activity_level"][
        ["astronaut_id", "timestamp", "value"]
    ].rename(columns={"value": "activity_level"})
    heart = source[source["variable"] == "heart_rate"].merge(
        activity, on=["astronaut_id", "timestamp"], how="left"
    )
    heart = heart[heart["activity_level"].isna() | (heart["activity_level"] == 0)]

    selected: list[pd.DataFrame] = []
    for variable, (field, accepted_units) in UNIT_MAP.items():
        rows = heart if variable == "heart_rate" else source[source["variable"] == variable]
        rows = rows[rows["unit_normalized"].isin(accepted_units)]
        if rows.empty:
            continue
        part = rows[["astronaut_id", "mission_day", "value", "source", "quality_normalized"]].copy()
        part["field"] = field
        selected.append(part)

    if not selected:
        raise ValueError("No supported variables with recognized units were found")

    mapped = pd.concat(selected, ignore_index=True)
    grouped = mapped.groupby(["astronaut_id", "mission_day", "field"], as_index=False).agg(
        value=("value", "median"),
        source_count=("value", "size"),
        source_names=("source", lambda values: "; ".join(sorted(set(map(str, values))))),
        quality_counts=("quality_normalized", lambda values: "; ".join(sorted(set(map(str, values))))),
    )
    values = grouped.pivot(index=["astronaut_id", "mission_day"], columns="field", values="value").reset_index()
    values.columns.name = None
    counts = grouped.groupby(["astronaut_id", "mission_day"], as_index=False)["source_count"].sum()
    provenance = grouped.groupby(["astronaut_id", "mission_day"], as_index=False).agg(
        source_names=("source_names", lambda items: "; ".join(sorted(set("; ".join(items).split("; "))))),
        source_variables=("field", lambda items: ",".join(sorted(set(items)))),
        quality_flags=("quality_counts", lambda items: "; ".join(sorted(set("; ".join(items).split("; "))))),
    )
    daily = values.merge(counts, on=["astronaut_id", "mission_day"], how="left").merge(
        provenance, on=["astronaut_id", "mission_day"], how="left"
    )

    for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS:
        if field not in daily:
            daily[field] = np.nan
    if "__bone_density_g_cm2" in daily:
        daily["bmd_drift_pct"] = np.nan
        for astronaut_id, indices in daily.groupby("astronaut_id").groups.items():
            person = daily.loc[indices].sort_values("mission_day")
            bone = person[person["__bone_density_g_cm2"].notna()]
            baseline = bone[bone["mission_day"] <= 0]
            if baseline.empty:
                continue
            anchor = float(baseline.iloc[-1]["__bone_density_g_cm2"])
            if not np.isfinite(anchor) or anchor <= 0:
                continue
            baseline_indices = person.index[person["mission_day"] <= 0]
            daily.loc[baseline_indices, "bmd_drift_pct"] = 0.0
            measured = person[person["__bone_density_g_cm2"].notna()]
            daily.loc[measured.index, "bmd_drift_pct"] = (
                (measured["__bone_density_g_cm2"].astype(float) - anchor) / anchor * 100.0
            )
    else:
        daily["bmd_drift_pct"] = np.nan

    daily["pulse_pressure_mmhg"] = daily["sbp_mmhg"] - daily["dbp_mmhg"]
    daily["sleep_efficiency_pct"] = (
        daily["sleep_duration_hrs"] / daily["sleep_time_in_bed_h"] * 100.0
    ).where(daily["sleep_time_in_bed_h"] > 0)

    # Radiation totals are calculated only for the mission segment. If any
    # daily rate is absent, cumulative exposure from that point onward is left
    # unknown instead of silently understating it.
    daily["cumulative_rad_msv"] = np.nan
    for _, indices in daily.groupby("astronaut_id").groups.items():
        person = daily.loc[indices].sort_values("mission_day")
        baseline_indices = person.index[person["mission_day"] <= 0]
        daily.loc[baseline_indices, "cumulative_rad_msv"] = 0.0
        mission = person[person["mission_day"] > 0]
        if mission.empty:
            continue
        rates = mission["daily_rad_rate_msv"].astype(float)
        valid_prefix = rates.notna().cummin()
        cumulative = rates.fillna(0.0).cumsum().where(valid_prefix)
        daily.loc[mission.index, "cumulative_rad_msv"] = cumulative.to_numpy()

    daily["gravity_g"] = np.where(daily["mission_day"] <= 0, 1.0, np.nan)
    daily["is_simulated"] = True
    daily = daily.sort_values(["astronaut_id", "mission_day"]).reset_index(drop=True)
    ordered = ["astronaut_id", "mission_day", *VITAL_COLUMNS, *ENVIRONMENT_COLUMNS,
               "source_count", "source_names", "source_variables", "quality_flags", "is_simulated"]
    return daily[list(dict.fromkeys(ordered))]


def save_normalized_measurements(output: Path = NORMALIZED_OUTPUT) -> pd.DataFrame:
    daily = normalize_measurements()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output, index=False)
    return daily


def local_dataset_summary() -> dict[str, Any]:
    daily = normalize_measurements()
    fields = VITAL_COLUMNS + ENVIRONMENT_COLUMNS
    coverage = {
        field: round(float(daily[field].notna().mean() * 100.0), 1)
        for field in fields
    }
    return {
        "dataset_id": "synthetic-long-measurements-v1",
        "data_origin": "synthetic_demo_only",
        "is_simulated": True,
        "source_file": "data/synthetic/measurements.csv",
        "normalized_file": str(NORMALIZED_OUTPUT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "astronaut_ids": sorted(daily["astronaut_id"].unique().tolist()),
        "astronaut_count": int(daily["astronaut_id"].nunique()),
        "daily_rows": int(len(daily)),
        "mission_day_range": [int(daily["mission_day"].min()), int(daily["mission_day"].max())],
        "field_coverage_pct": coverage,
        "unsupported_model_inputs": [
            field for field in fields if coverage.get(field, 0.0) == 0.0
        ],
        "note": "OSDR/NLSP files are discovered and cached separately; only study-specific reviewed mappers may convert them into ML inputs.",
    }


def local_forecast_request(astronaut_id: str, mission_day: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the same forecast request shape from the repository demo dataset."""
    daily = normalize_measurements()
    person = daily[daily["astronaut_id"] == astronaut_id].sort_values("mission_day")
    if person.empty:
        raise ValueError(f"Unknown astronaut_id in local demo dataset: {astronaut_id}")
    max_day = int(person[person["mission_day"] > 0]["mission_day"].max())
    selected_day = max_day if mission_day is None else int(mission_day)
    if selected_day < 1 or selected_day > max_day:
        raise ValueError(f"mission_day must be between 1 and {max_day}")

    baseline = person[person["mission_day"].between(-13, 0)].sort_values("mission_day")
    mission = person[person["mission_day"].between(max(1, selected_day - 13), selected_day)].sort_values("mission_day")
    if len(baseline) != 14 or len(mission) == 0 or int(mission.iloc[-1]["mission_day"]) != selected_day:
        raise ValueError("The local dataset does not contain the required consecutive baseline/mission days")

    fields = VITAL_COLUMNS + ENVIRONMENT_COLUMNS
    def as_observations(frame: pd.DataFrame) -> list[dict[str, float | None]]:
        result = []
        for _, row in frame.iterrows():
            point: dict[str, float | None] = {}
            for field in fields:
                value = row[field]
                point[field] = float(value) if pd.notna(value) and np.isfinite(float(value)) else None
            result.append(point)
        return result

    request = {
        "astronaut_id": astronaut_id,
        "earth_baseline": as_observations(baseline),
        "mission_telemetry": as_observations(mission),
        "mission_day": selected_day,
        # The source contains no validated pre-medical fields; defaults are
        # explicit imputation for the synthetic demonstration only.
        "pre_medical": {
            "prior_arrhythmia_flag": False,
            "vo2_max_earth": 45.0,
            "baseline_t_score": 0.0,
            "baseline_optic_nerve_mm": 3.0,
        },
        "data_origin": "repository_synthetic_long_measurements",
    }
    latest = request["mission_telemetry"][-1]
    baseline_missing = [field for field in fields if not any(item[field] is not None for item in request["earth_baseline"])]
    mission_missing = [field for field in fields if latest[field] is None]
    quality = {
        "data_origin": request["data_origin"],
        "is_simulated": True,
        "mission_day": selected_day,
        "latest_observed_field_count": len(fields) - len(mission_missing),
        "expected_field_count": len(fields),
        "latest_missing_fields": mission_missing,
        "baseline_missing_fields": baseline_missing,
        "pre_medical_fields_imputed": ["prior_arrhythmia_flag", "vo2_max_earth", "baseline_t_score", "baseline_optic_nerve_mm"],
        "note": "Missing fields are model-imputed; forecasts and alert logic are synthetic demonstrations, not clinical estimates.",
    }
    return request, quality
