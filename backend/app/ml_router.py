"""Non-breaking REST endpoints for synthetic-only ML pipeline demonstrations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ml.data_loader import ENVIRONMENT_COLUMNS, PREMED_COLUMNS, VITAL_COLUMNS, build_synthetic_corpus
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


class PreMedical(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    prior_arrhythmia_flag: bool = False
    vo2_max_earth: float = 45.0
    baseline_t_score: float = 0.0
    baseline_optic_nerve_mm: float = 3.0


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
