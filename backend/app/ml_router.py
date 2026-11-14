"""Non-breaking REST endpoints for synthetic-only ML pipeline demonstrations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ml.data_loader import ENVIRONMENT_COLUMNS, PREMED_COLUMNS, VITAL_COLUMNS, build_synthetic_corpus
from ml.research_data import local_dataset_summary, local_forecast_request
from ml.serving import load_model_registry, model_info, run_forecast

router = APIRouter(prefix="/ml", tags=["ML research demo"])


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    resting_hr_bpm: float | None = None
    hrv_rmssd_ms: float | None = None
    sbp_mmhg: float | None = None
    dbp_mmhg: float | None = None
    pulse_pressure_mmhg: float | None = None
    sleep_duration_hrs: float | None = None
    sleep_efficiency_pct: float | None = None
    winscat_rt_ms: float | None = None
    winscat_accuracy_pct: float | None = None
    cumulative_rad_msv: float | None = None
    daily_rad_rate_msv: float | None = None
    wbc_count_k_ul: float | None = None
    nlr_ratio: float | None = None
    bmd_drift_pct: float | None = None
    serum_calcium_mg_dl: float | None = None
    urinary_calcium_mg_day: float | None = None
    ared_exercise_load_pct: float | None = None
    gravity_g: float | None = None
    cabin_co2_mmhg: float | None = None
    cabin_po2_mmhg: float | None = None
    cabin_pressure_psi: float | None = None

    @model_validator(mode="after")
    def basic_physical_sanity(self):
        # Broad input-integrity bounds only; these are not clinical limits.
        ranges = {
            "resting_hr_bpm": (20, 240), "hrv_rmssd_ms": (0, 500),
            "sbp_mmhg": (40, 300), "dbp_mmhg": (20, 200), "pulse_pressure_mmhg": (0, 250),
            "sleep_duration_hrs": (0, 24), "sleep_efficiency_pct": (0, 100),
            "winscat_rt_ms": (50, 10000), "winscat_accuracy_pct": (0, 100),
            "cumulative_rad_msv": (0, 100000), "daily_rad_rate_msv": (0, 10000),
            "wbc_count_k_ul": (0, 200), "nlr_ratio": (0, 100), "bmd_drift_pct": (-100, 100),
            "serum_calcium_mg_dl": (0, 50), "urinary_calcium_mg_day": (0, 10000),
            "ared_exercise_load_pct": (0, 250), "gravity_g": (0, 1.5),
            "cabin_co2_mmhg": (0, 50), "cabin_po2_mmhg": (0, 500), "cabin_pressure_psi": (0, 50),
        }
        for field, (minimum, maximum) in ranges.items():
            value = getattr(self, field)
            if value is not None and not minimum <= value <= maximum:
                raise ValueError(f"{field} must be between {minimum} and {maximum}; these are broad input sanity bounds, not clinical limits")
        if self.sbp_mmhg is not None and self.dbp_mmhg is not None and self.sbp_mmhg < self.dbp_mmhg:
            raise ValueError("sbp_mmhg must be greater than or equal to dbp_mmhg")
        return self


class PreMedical(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    prior_arrhythmia_flag: bool = False
    vo2_max_earth: float = 45.0
    baseline_t_score: float = 0.0
    baseline_optic_nerve_mm: float = 3.0

    @model_validator(mode="after")
    def basic_value_sanity(self):
        bounds = {
            "vo2_max_earth": (0, 100),
            "baseline_t_score": (-10, 10),
            "baseline_optic_nerve_mm": (0, 10),
        }
        for field, (minimum, maximum) in bounds.items():
            value = getattr(self, field)
            if not minimum <= value <= maximum:
                raise ValueError(f"{field} must be between {minimum} and {maximum}")
        return self


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    astronaut_id: str = Field(min_length=1, max_length=80)
    earth_baseline: list[Observation] = Field(min_length=14, max_length=14)
    mission_telemetry: list[Observation] = Field(min_length=1, max_length=14)
    mission_day: int | None = Field(default=None, ge=1, le=70)
    pre_medical: PreMedical = Field(default_factory=PreMedical)

    @model_validator(mode="after")
    def mission_day_covers_history(self):
        if self.mission_day is not None and self.mission_day < len(self.mission_telemetry):
            raise ValueError("mission_day must be at least the number of supplied mission observations")
        return self


def registry_for_request(request: Request) -> dict[str, Any]:
    registry = getattr(request.app.state, "ml_registry", None)
    if registry is None:
        registry = load_model_registry()
        request.app.state.ml_registry = registry
    return registry


@router.post("/forecast")
def forecast(payload: ForecastRequest, request: Request) -> dict[str, Any]:
    registry = registry_for_request(request)
    if not any(name in registry["models"] for name in ("heart", "nerve", "immune", "bone")):
        raise HTTPException(status_code=503, detail="No forecast model artifacts are available. Run backend/ml/train_ml.py.")
    try:
        result = run_forecast(payload.model_dump(), registry)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Could not build the request feature window: {exc}") from exc
    result["astronaut_id"] = payload.astronaut_id
    return result


@router.get("/model-info")
def get_model_info(request: Request) -> dict[str, Any]:
    return model_info(registry_for_request(request))


@router.get("/data-status")
def get_data_status(request: Request) -> dict[str, Any]:
    """Show the collection/processing/training inputs used by this checkout."""
    from ml.data_loader import RAW_NLSP, RAW_OSDR
    from ml.train_ml import DATA_PATH

    try:
        dataset = local_dataset_summary()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Local demo data is unavailable: {exc}") from exc

    osdr_files = sorted(path.name for path in RAW_OSDR.glob("*") if path.is_file()) if RAW_OSDR.exists() else []
    nlsp_files = sorted(path.name for path in RAW_NLSP.rglob("*") if path.is_file() and path.suffix.lower() in {".csv", ".tsv"}) if RAW_NLSP.exists() else []
    registry = registry_for_request(request)
    return {
        "pipeline_id": "astroguard-unified-demo-v1",
        "stages": {
            "collection": {"osdr_cached_files": osdr_files, "nlsp_local_files": nlsp_files},
            "processing": dataset,
            "training": {
                "dataset_available": DATA_PATH.is_file(),
                "dataset": "backend/data/processed/synthetic_demo_70day.csv",
                "data_origin": "synthetic_demo_only",
                "models_loaded": [name for name, status in registry["status"].items() if status["loaded"]],
                "metrics": registry.get("training_metrics"),
            },
        },
        "clinical_use": False,
        "note": "OSDR/NLSP raw files are catalogued separately and are not silently converted into training labels.",
    }


@router.get("/forecast-from-dataset/{astronaut_id}")
def forecast_from_dataset(astronaut_id: str, request: Request, mission_day: int | None = None) -> dict[str, Any]:
    """Exercise the local collection-to-processing-to-forecast path end to end."""
    registry = registry_for_request(request)
    if not any(name in registry["models"] for name in ("heart", "nerve", "immune", "bone")):
        raise HTTPException(status_code=503, detail="No forecast model artifacts are available. Run the unified ML pipeline.")
    try:
        request_data, source_quality = local_forecast_request(astronaut_id, mission_day)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Local demo data is unavailable: {exc}") from exc
    except ValueError as exc:
        status_code = 404 if "Unknown astronaut_id" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    result = run_forecast(request_data, registry)
    result["astronaut_id"] = astronaut_id
    result["data_quality"]["source_dataset"] = source_quality
    return result


@router.get("/demo-mission")
def demo_mission(request: Request) -> dict[str, Any]:
    registry = registry_for_request(request)
    if not any(name in registry["models"] for name in ("heart", "nerve", "immune", "bone")):
        raise HTTPException(status_code=503, detail="No forecast model artifacts are available. Run backend/ml/train_ml.py.")
    corpus = build_synthetic_corpus(astronauts=1, mission_days=30, seed=2042)
    crew = corpus[corpus.astronaut_id == "SIM-001"].sort_values("mission_day")
    earth = crew[(crew.mission_day >= -14) & (crew.mission_day < 0)]
    flags = {name: earth[name].iloc[0].item() if hasattr(earth[name].iloc[0], "item") else earth[name].iloc[0] for name in PREMED_COLUMNS}
    baseline = [{field: float(row[field]) for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS} for _, row in earth.iterrows()]
    mission = crew[~crew.is_baseline].copy()
    mission.loc[mission.mission_day == 12, "cabin_co2_mmhg"] = 3.9
    mission.loc[mission.mission_day == 22, "ared_exercise_load_pct"] = 28.0
    timeline = []
    observed: list[dict[str, float]] = []
    for _, row in mission.iterrows():
        point = {field: float(row[field]) for field in VITAL_COLUMNS + ENVIRONMENT_COLUMNS}
        observed.append(point)
        request_data = {
            "astronaut_id": "SIM-001",
            "earth_baseline": baseline,
            "mission_telemetry": observed[-14:],
            "mission_day": int(row.mission_day),
            "pre_medical": flags,
        }
        forecast_result = run_forecast(request_data, registry)
        timeline.append({
            "day": int(row.mission_day),
            "telemetry": point,
            "sudden_drop_detected": forecast_result["sudden_drop_detected"],
            "acute_alerts": forecast_result["acute_alerts"],
            "systems": forecast_result["systems"],
        })
    return {
        "scenario_id": "synthetic-demo-30-day-v1",
        "data_origin": "synthetic_demo_only",
        "clinical_use": False,
        "timeline": timeline,
        "scenario_events": [
            {"day": 12, "event": "synthetic cabin CO2 spike", "value": 3.9, "unit": "mmHg"},
            {"day": 22, "event": "synthetic ARED exercise-load drop", "value": 28.0, "unit": "%"},
        ],
        "review_note": "Every value and forecast is synthetic demonstration output, not a medical estimate or intervention instruction.",
    }
