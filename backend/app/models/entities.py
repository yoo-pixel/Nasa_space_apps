import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    destination: Mapped[str] = mapped_column(String(120), default="Low Earth Orbit")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    astronauts: Mapped[list["Astronaut"]] = relationship(back_populates="mission")

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(40), default="medical_reviewer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(140), unique=True)
    organization: Mapped[str] = mapped_column(String(140), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    dataset_version: Mapped[str] = mapped_column(String(80), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="available")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="data_source")

class Astronaut(Base):
    __tablename__ = "astronauts"
    __table_args__ = (Index("ix_astronaut_mission_status", "mission_id", "monitoring_status"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("missions.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(140))
    callsign: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str] = mapped_column(String(100), default="Flight crew")
    nationality: Mapped[str] = mapped_column(String(80), default="")
    avatar_color: Mapped[str] = mapped_column(String(20), default="#198D6D")
    monitoring_status: Mapped[str] = mapped_column(String(40), default="stable")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    mission: Mapped["Mission"] = relationship(back_populates="astronauts")
    medical_history: Mapped[list["MedicalHistory"]] = relationship(back_populates="astronaut", cascade="all, delete-orphan")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="astronaut", cascade="all, delete-orphan")
    baselines: Mapped[list["MetricBaseline"]] = relationship(back_populates="astronaut", cascade="all, delete-orphan")
    analyses: Mapped[list["AnalysisResult"]] = relationship(back_populates="astronaut", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="astronaut", cascade="all, delete-orphan")

class MedicalHistory(Base):
    __tablename__ = "medical_history"
    __table_args__ = (Index("ix_medical_history_astronaut_date", "astronaut_id", "recorded_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    recorded_by: Mapped[str] = mapped_column(String(120), default="Demo medical team")
    source: Mapped[str] = mapped_column(String(160), default="manual")
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(120), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    astronaut: Mapped["Astronaut"] = relationship(back_populates="medical_history")

class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (Index("ix_learning_astronaut_started", "astronaut_id", "started_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_by: Mapped[str] = mapped_column(String(120), default="Medical reviewer")

class PersonalizedProfile(Base):
    __tablename__ = "personalized_profiles"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_sessions.id", ondelete="CASCADE"), unique=True, index=True)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="approved")
    approved_by: Mapped[str] = mapped_column(String(120), default="Medical reviewer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class BoneHealthAssessment(Base):
    __tablename__ = "bone_health_assessments"
    __table_args__ = (Index("ix_bone_astronaut_recorded", "astronaut_id", "recorded_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    assessment_type: Mapped[str] = mapped_column(String(40))
    metric: Mapped[str] = mapped_column(String(80))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(160))
    source_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")

class RadiationExposureRecord(Base):
    __tablename__ = "radiation_exposure_records"
    __table_args__ = (Index("ix_radiation_astronaut_measured", "astronaut_id", "measured_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    dosimeter_id: Mapped[str] = mapped_column(String(100))
    exposure_type: Mapped[str] = mapped_column(String(30))
    measurement_basis: Mapped[str] = mapped_column(String(30), default="interval")
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(160))
    mission_phase: Mapped[str] = mapped_column(String(100), default="")
    event: Mapped[str] = mapped_column(String(160), default="")
    shielding: Mapped[str] = mapped_column(String(160), default="")
    source_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")

class MetricBaseline(Base):
    __tablename__ = "metric_baselines"
    __table_args__ = (Index("ix_baseline_astronaut_metric", "astronaut_id", "metric", unique=True),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(60))
    unit: Mapped[str] = mapped_column(String(30))
    median: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(120), default="Personal historical median and robust spread")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    astronaut: Mapped["Astronaut"] = relationship(back_populates="baselines")

class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (Index("ix_measurement_astronaut_metric_time", "astronaut_id", "metric", "measured_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    metric: Mapped[str] = mapped_column(String(60), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="manual")
    symptoms: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    astronaut: Mapped["Astronaut"] = relationship(back_populates="measurements")
    data_source: Mapped["DataSource | None"] = relationship(back_populates="measurements")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (Index("ix_analysis_astronaut_created", "astronaut_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    model_version: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(Text)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    astronaut: Mapped["Astronaut"] = relationship(back_populates="analyses")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="analysis")

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alert_status_priority", "status", "priority"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    astronaut_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("analysis_results.id"), nullable=True)
    measurement_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("measurements.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    metric: Mapped[str] = mapped_column(String(60))
    observed_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(30), default="review")
    status: Mapped[str] = mapped_column(String(30), default="open")
    reviewer_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    astronaut: Mapped["Astronaut"] = relationship(back_populates="alerts")
    analysis: Mapped["AnalysisResult | None"] = relationship(back_populates="alerts")
