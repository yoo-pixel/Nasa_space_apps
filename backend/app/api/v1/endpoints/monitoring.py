from collections import defaultdict
from datetime import datetime, timezone
from math import floor
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.ml.baseline import robust_band
from app.models import Astronaut, BoneHealthAssessment, LearningSession, MedicalHistory, Measurement, MetricBaseline, PersonalizedProfile, RadiationExposureRecord
from app.models.entities import utcnow
from app.schemas.schemas import BoneHealthCreate, BoneHealthOut, HealthDomainOut, LearningOut, LearningStart, MonitoringSummary, ProfileApproval, RadiationExposureCreate, RadiationExposureOut

router = APIRouter()


def _astronaut_or_404(db: Session, astronaut_id: UUID) -> Astronaut:
    person = db.get(Astronaut, astronaut_id)
    if person is None:
        raise HTTPException(404, "Astronaut not found")
    return person


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _learning_snapshot(db: Session, astronaut_id: UUID, session: LearningSession | None) -> dict:
    if session is None:
        return {
            "astronaut_id": astronaut_id, "session_id": None, "started_at": None, "started_by": None, "day_number": 0,
            "elapsed_days": 0, "status": "not_started", "phase": "Not started", "distinct_days": 0,
            "reading_count": 0, "metric_count": 0, "requirements": [], "timeline": [],
            "profile_id": None, "profile_status": None,
        }

    started = _aware(session.started_at)
    elapsed_days = max(0, floor((_aware(utcnow()) - started).total_seconds() / 86400))
    day_number = min(14, elapsed_days + 1)
    rows = list(db.scalars(select(Measurement).where(
        Measurement.astronaut_id == astronaut_id,
        Measurement.measured_at >= session.started_at,
        Measurement.measured_at <= utcnow(),
    )))
    valid_days = {_aware(row.measured_at).date().isoformat() for row in rows}
    metrics = {row.metric for row in rows}
    distinct_days = len(valid_days)
    reading_count = len(rows)
    metric_count = len(metrics)
    requirements = [
        {"key": "duration", "label": "14 full days elapsed", "required": 14, "actual": elapsed_days, "met": elapsed_days >= 14},
        {"key": "coverage", "label": "Measurements on 10 separate days", "required": 10, "actual": distinct_days, "met": distinct_days >= 10},
        {"key": "readings", "label": "At least 30 valid readings", "required": 30, "actual": reading_count, "met": reading_count >= 30},
        {"key": "metrics", "label": "At least 2 monitored metrics", "required": 2, "actual": metric_count, "met": metric_count >= 2},
    ]
    sufficient = all(item["met"] for item in requirements)
    if elapsed_days >= 14:
        status = "ready_for_review" if sufficient else "needs_more_data"
        phase = "Ready for medical review" if sufficient else "Collection extension"
    else:
        status = "collecting"
        phase = "Validation" if day_number <= 3 else "Baseline" if day_number <= 7 else "Trend analysis" if day_number <= 10 else "Refinement"
    phase_ranges = [("Validation", 1, 3), ("Baseline", 4, 7), ("Trend analysis", 8, 10), ("Refinement", 11, 14)]
    timeline = [{"label": label, "days": f"{first}–{last}", "complete": day_number > last or elapsed_days >= 14, "current": first <= day_number <= last and elapsed_days < 14} for label, first, last in phase_ranges]
    profile = db.scalar(select(PersonalizedProfile).where(PersonalizedProfile.session_id == session.id))
    return {
        "astronaut_id": astronaut_id, "session_id": session.id, "started_at": session.started_at, "started_by": session.started_by,
        "day_number": day_number, "elapsed_days": elapsed_days,
        "status": "profile_active" if profile else status, "phase": phase,
        "distinct_days": distinct_days, "reading_count": reading_count, "metric_count": metric_count,
        "requirements": requirements, "timeline": timeline,
        "profile_id": profile.id if profile else None, "profile_status": profile.status if profile else None,
    }


@router.get("/dashboard/monitoring-summary", response_model=MonitoringSummary)
def monitoring_summary(db: Session = Depends(get_db)):
    latest_sessions = []
    astronaut_ids = list(db.scalars(select(Astronaut.id)))
    for astronaut_id in astronaut_ids:
        session = db.scalar(select(LearningSession).where(LearningSession.astronaut_id == astronaut_id).order_by(LearningSession.started_at.desc()).limit(1))
        if session:
            latest_sessions.append(_learning_snapshot(db, astronaut_id, session)["status"])
    return {
        "sessions_collecting": sum(status in {"collecting", "needs_more_data"} for status in latest_sessions),
        "sessions_ready_for_review": sum(status == "ready_for_review" for status in latest_sessions),
        "histories_awaiting_review": db.scalar(select(func.count(MedicalHistory.id)).where(MedicalHistory.verification_status == "unverified")) or 0,
        "bone_record_count": db.scalar(select(func.count(BoneHealthAssessment.id))) or 0,
        "radiation_record_count": db.scalar(select(func.count(RadiationExposureRecord.id))) or 0,
        "active_profile_count": db.scalar(select(func.count(PersonalizedProfile.id)).where(PersonalizedProfile.status == "approved")) or 0,
    }


@router.get("/astronauts/{astronaut_id}/learning", response_model=LearningOut)
def get_learning(astronaut_id: UUID, db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    session = db.scalar(select(LearningSession).where(LearningSession.astronaut_id == astronaut_id).order_by(LearningSession.started_at.desc()).limit(1))
    return _learning_snapshot(db, astronaut_id, session)


@router.post("/astronauts/{astronaut_id}/learning", response_model=LearningOut, status_code=201)
def start_learning(astronaut_id: UUID, payload: LearningStart, db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    history = list(db.scalars(select(MedicalHistory).where(MedicalHistory.astronaut_id == astronaut_id)))
    pending = [entry for entry in history if entry.verification_status == "unverified"]
    if pending:
        raise HTTPException(409, "Review every medical-history entry as verified or not verified before starting learning.")
    previous = db.scalar(select(LearningSession).where(LearningSession.astronaut_id == astronaut_id).order_by(LearningSession.started_at.desc()).limit(1))
    if previous:
        snapshot = _learning_snapshot(db, astronaut_id, previous)
        if snapshot["status"] != "profile_active":
            if snapshot["status"] == "ready_for_review":
                raise HTTPException(409, "This learning session is ready for medical review.")
            raise HTTPException(409, "A learning session is already in progress.")
    session = LearningSession(astronaut_id=astronaut_id, started_by=payload.started_by)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _learning_snapshot(db, astronaut_id, session)


@router.post("/learning/{session_id}/approve", response_model=LearningOut)
def approve_profile(session_id: UUID, payload: ProfileApproval, db: Session = Depends(get_db)):
    session = db.get(LearningSession, session_id)
    if session is None:
        raise HTTPException(404, "Learning session not found")
    snapshot = _learning_snapshot(db, session.astronaut_id, session)
    if snapshot["status"] == "profile_active":
        return snapshot
    if snapshot["status"] != "ready_for_review":
        raise HTTPException(409, "The learning requirements are not complete. Calendar time alone cannot create a profile.")
    rows = list(db.scalars(select(Measurement).where(
        Measurement.astronaut_id == session.astronaut_id,
        Measurement.measured_at >= session.started_at,
        Measurement.measured_at <= utcnow(),
    )))
    by_metric: dict[str, list[Measurement]] = defaultdict(list)
    for row in rows:
        by_metric[row.metric].append(row)
    now = utcnow()
    for metric, items in by_metric.items():
        if len(items) < 10:
            continue
        values = [item.value for item in items]
        unit = items[-1].unit
        center, low, high = robust_band(values, floor=0.1)
        baseline = db.scalar(select(MetricBaseline).where(MetricBaseline.astronaut_id == session.astronaut_id, MetricBaseline.metric == metric))
        values_to_set = {
            "unit": unit, "median": round(center, 3), "lower_bound": round(low, 3), "upper_bound": round(high, 3),
            "sample_count": len(items), "method": "Personal observed median ± 3 robust spreads · reviewer approved",
            "updated_at": now,
        }
        if baseline:
            for key, value in values_to_set.items():
                setattr(baseline, key, value)
        else:
            db.add(MetricBaseline(astronaut_id=session.astronaut_id, metric=metric, **values_to_set))
    profile = PersonalizedProfile(session_id=session.id, astronaut_id=session.astronaut_id, status="approved", approved_by=payload.approved_by)
    db.add(profile)
    db.commit()
    return _learning_snapshot(db, session.astronaut_id, session)


@router.get("/astronauts/{astronaut_id}/bone-health", response_model=list[BoneHealthOut])
def list_bone_health(astronaut_id: UUID, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    return list(db.scalars(select(BoneHealthAssessment).where(BoneHealthAssessment.astronaut_id == astronaut_id).order_by(BoneHealthAssessment.recorded_at.desc()).limit(limit)))


@router.post("/astronauts/{astronaut_id}/bone-health", response_model=BoneHealthOut, status_code=201)
def create_bone_assessment(astronaut_id: UUID, payload: BoneHealthCreate, db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    item = BoneHealthAssessment(astronaut_id=astronaut_id, recorded_at=payload.recorded_at or utcnow(), **payload.model_dump(exclude={"recorded_at"}))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/astronauts/{astronaut_id}/radiation", response_model=list[RadiationExposureOut])
def list_radiation(astronaut_id: UUID, exposure_type: str = "", limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    stmt = select(RadiationExposureRecord).where(RadiationExposureRecord.astronaut_id == astronaut_id).order_by(RadiationExposureRecord.measured_at.desc()).limit(limit)
    if exposure_type:
        stmt = stmt.where(RadiationExposureRecord.exposure_type == exposure_type)
    return list(db.scalars(stmt))


@router.post("/astronauts/{astronaut_id}/radiation", response_model=RadiationExposureOut, status_code=201)
def create_radiation_record(astronaut_id: UUID, payload: RadiationExposureCreate, db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    item = RadiationExposureRecord(astronaut_id=astronaut_id, measured_at=payload.measured_at or utcnow(), **payload.model_dump(exclude={"measured_at"}))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/astronauts/{astronaut_id}/health-domains", response_model=list[HealthDomainOut])
def health_domains(astronaut_id: UUID, db: Session = Depends(get_db)):
    _astronaut_or_404(db, astronaut_id)
    readings = list(db.scalars(select(Measurement).where(Measurement.astronaut_id == astronaut_id)))
    bone = list(db.scalars(select(BoneHealthAssessment).where(BoneHealthAssessment.astronaut_id == astronaut_id)))
    radiation = list(db.scalars(select(RadiationExposureRecord).where(RadiationExposureRecord.astronaut_id == astronaut_id)))
    cardio = [row for row in readings if row.metric in {"heart_rate", "systolic_bp", "diastolic_bp"}]

    def sourced_status(items):
        if not items:
            return "insufficient", "No source records are available yet."
        if any(not item.source_verified for item in items):
            return "awaiting_medical_review", "Records exist; at least one source has not been verified."
        return "data_available", "Source records are available. No risk score is calculated."

    bone_status, bone_detail = sourced_status(bone)
    rad_status, rad_detail = sourced_status(radiation)
    domains = [
        {"key": "cardiovascular", "label": "Cardiovascular", "status": "data_available" if cardio else "insufficient", "record_count": len(cardio), "detail": f"{len(cardio)} heart-rate or blood-pressure readings; personal baseline comparison only." if cardio else "No heart-rate or blood-pressure readings are recorded."},
        {"key": "bone", "label": "Bone health", "status": bone_status, "record_count": len(bone), "detail": bone_detail},
        {"key": "radiation", "label": "Radiation exposure", "status": rad_status, "record_count": len(radiation), "detail": rad_detail},
        {"key": "muscle_fitness", "label": "Muscle & fitness", "status": "not_monitored", "record_count": 0, "detail": "Exercise-session capture is not connected."},
        {"key": "vision_neuro", "label": "Vision & neuro", "status": "not_monitored", "record_count": 0, "detail": "No vision or neuro observations are recorded."},
        {"key": "immune", "label": "Immune", "status": "not_monitored", "record_count": 0, "detail": "No immune observations are recorded."},
        {"key": "sleep_behavioral", "label": "Sleep & behavioral", "status": "not_monitored", "record_count": 0, "detail": "No sleep or behavioral observations are recorded."},
        {"key": "nutrition_renal", "label": "Nutrition & renal", "status": "not_monitored", "record_count": 0, "detail": "No nutrition, hydration, or renal observations are recorded."},
    ]
    return domains
