from datetime import datetime
from math import isfinite
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from app.schemas.common import ORMModel

class MissionCreate(ORMModel):
    name: str
    destination: str = "Low Earth Orbit"
    status: str = "active"
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str = ""
class MissionOut(MissionCreate):
    id: UUID
class DataSourceOut(ORMModel):
    id: UUID
    name: str
    organization: str
    description: str
    dataset_version: str
    url: str
    is_simulated: bool
    status: str
class AstronautCreate(ORMModel):
    mission_id: UUID
    full_name: str
    callsign: str
    role: str = "Flight crew"
    nationality: str = ""
    avatar_color: str = "#198D6D"
    monitoring_status: str = "stable"
    notes: str = ""
class AstronautPatch(ORMModel):
    full_name: str | None = None
    callsign: str | None = None
    role: str | None = None
    nationality: str | None = None
    monitoring_status: str | None = None
    notes: str | None = None
class MissionBrief(ORMModel):
    id: UUID
    name: str
    status: str
    destination: str
class AstronautOut(ORMModel):
    id: UUID
    mission_id: UUID
    full_name: str
    callsign: str
    role: str
    nationality: str
    avatar_color: str
    monitoring_status: str
    notes: str
    mission: MissionBrief
class MedicalHistoryCreate(ORMModel):
    category: str
    summary: str
    recorded_at: datetime | None = None
    recorded_by: str = "Medical team"
    source: str = "manual"
class MedicalHistoryPatch(ORMModel):
    category: str | None = None
    summary: str | None = None
    recorded_by: str | None = None
    verification_status: str | None = None
    review_notes: str | None = None
    reviewed_by: str | None = None

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"unverified", "verified", "not_verified"}:
            raise ValueError("Verification status must be unverified, verified, or not_verified")
        return value
class MedicalHistoryOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    category: str
    summary: str
    recorded_at: datetime
    recorded_by: str
    source: str
    verification_status: str
    review_notes: str
    reviewed_by: str
    reviewed_at: datetime | None

class LearningOut(ORMModel):
    astronaut_id: UUID
    session_id: UUID | None
    started_at: datetime | None
    started_by: str | None
    day_number: int
    elapsed_days: int
    status: str
    phase: str
    distinct_days: int
    reading_count: int
    metric_count: int
    requirements: list[dict]
    timeline: list[dict]
    profile_id: UUID | None
    profile_status: str | None

class LearningStart(ORMModel):
    started_by: str = "Medical reviewer"

    @field_validator("started_by")
    @classmethod
    def starter_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reviewer name is required")
        return value.strip()

class ProfileApproval(ORMModel):
    approved_by: str = "Medical reviewer"

    @field_validator("approved_by")
    @classmethod
    def reviewer_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reviewer name is required")
        return value.strip()

class BoneHealthCreate(ORMModel):
    assessment_type: str
    metric: str
    value: float = Field(allow_inf_nan=False)
    unit: str
    recorded_at: datetime | None = None
    source: str
    source_verified: bool = False
    notes: str = ""

    @field_validator("assessment_type")
    @classmethod
    def supported_assessment_type(cls, value: str) -> str:
        allowed = {"scan", "turnover_marker", "exercise", "nutrition"}
        if value not in allowed:
            raise ValueError("Assessment type must be scan, turnover_marker, exercise, or nutrition")
        return value

    @field_validator("metric", "unit", "source")
    @classmethod
    def nonempty_labels(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be empty")
        return value.strip()

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("Value must be finite")
        return value

class BoneHealthOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    assessment_type: str
    metric: str
    value: float
    unit: str
    recorded_at: datetime
    source: str
    source_verified: bool
    notes: str

class RadiationExposureCreate(ORMModel):
    dosimeter_id: str
    exposure_type: str
    measurement_basis: str = "interval"
    value: float = Field(gt=0, allow_inf_nan=False)
    unit: str
    measured_at: datetime | None = None
    source: str
    mission_phase: str = ""
    event: str = ""
    shielding: str = ""
    source_verified: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def check_exposure_units(self):
        units = {
            "absorbed": {"Gy", "mGy", "µGy", "uGy"},
            "equivalent": {"Sv", "mSv", "µSv", "uSv"},
            "effective": {"Sv", "mSv", "µSv", "uSv"},
            "dose_rate": {"Gy/h", "mGy/h", "µGy/h", "uGy/h", "Sv/h", "mSv/h", "µSv/h", "uSv/h"},
        }
        if self.exposure_type not in units:
            raise ValueError("Exposure type must be absorbed, equivalent, effective, or dose_rate")
        allowed_basis = {"rate"} if self.exposure_type == "dose_rate" else {"interval", "cumulative"}
        if self.measurement_basis not in allowed_basis:
            raise ValueError("Dose records must be interval or cumulative; dose-rate records must use rate")
        if self.unit not in units[self.exposure_type]:
            raise ValueError("Unit does not match the selected radiation exposure type")
        if not self.dosimeter_id.strip() or not self.source.strip():
            raise ValueError("Dosimeter ID and source are required")
        return self

class RadiationExposureOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    dosimeter_id: str
    exposure_type: str
    measurement_basis: str
    value: float
    unit: str
    measured_at: datetime
    source: str
    mission_phase: str
    event: str
    shielding: str
    source_verified: bool
    notes: str

class HealthDomainOut(ORMModel):
    key: str
    label: str
    status: str
    record_count: int
    detail: str

class MonitoringSummary(ORMModel):
    sessions_collecting: int
    sessions_ready_for_review: int
    histories_awaiting_review: int
    bone_record_count: int
    radiation_record_count: int
    active_profile_count: int
class MeasurementCreate(ORMModel):
    metric: str
    value: float = Field(allow_inf_nan=False)
    unit: str
    measured_at: datetime | None = None
    source_type: str = "manual"
    symptoms: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("metric")
    @classmethod
    def supported_metric(cls, value: str) -> str:
        allowed = {"heart_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"}
        if value not in allowed:
            raise ValueError("Unsupported metric for the current demonstration data model")
        return value

    @field_validator("value")
    @classmethod
    def check_value_range(cls, value: float, info) -> float:
        limits = {
            "heart_rate": (20, 240), "spo2": (50, 100), "temperature": (30, 43),
            "systolic_bp": (50, 250), "diastolic_bp": (30, 150),
        }
        metric = info.data.get("metric")
        if not isfinite(value):
            raise ValueError("Measurement value must be finite")
        if metric in limits and not limits[metric][0] <= value <= limits[metric][1]:
            raise ValueError("Measurement is outside the accepted input range")
        return value

    @model_validator(mode="after")
    def match_metric_unit(self):
        units = {"heart_rate": "bpm", "spo2": "%", "temperature": "°C", "systolic_bp": "mmHg", "diastolic_bp": "mmHg"}
        if units.get(self.metric) != self.unit:
            raise ValueError("Unit does not match the selected metric")
        if self.source_type not in {"manual", "simulated"}:
            raise ValueError("Source type must be manual or simulated until a source import is implemented")
        return self
class MeasurementOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    data_source_id: UUID | None
    metric: str
    value: float
    unit: str
    measured_at: datetime
    source_type: str
    symptoms: list[str]
    notes: str
class BaselineOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    metric: str
    unit: str
    median: float
    lower_bound: float
    upper_bound: float
    sample_count: int
    method: str
    updated_at: datetime
class AnalysisOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    model_name: str
    model_version: str
    summary: str
    findings: list[dict]
    anomaly_score: float | None
    needs_review: bool
    created_at: datetime
class AlertOut(ORMModel):
    id: UUID
    astronaut_id: UUID
    analysis_id: UUID | None
    measurement_id: UUID | None
    title: str
    metric: str
    observed_value: float
    unit: str
    baseline_value: float | None
    explanation: str
    priority: str
    status: str
    reviewer_notes: str
    reviewed_by: str
    created_at: datetime
    reviewed_at: datetime | None
class AlertPatch(ORMModel):
    status: str | None = None
    reviewer_notes: str | None = None
    reviewed_by: str | None = None
class DashboardSummary(ORMModel):
    astronaut_count: int
    measurement_count: int
    active_alert_count: int
    review_count: int
    mission_name: str
    mission_start_date: datetime | None
    recent_measurements: list[dict]
    recent_alerts: list[dict]
