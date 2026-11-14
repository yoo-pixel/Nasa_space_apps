from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.db.dependencies import get_db
from app.models import Alert, AnalysisResult, Astronaut, DataSource, MedicalHistory, Measurement, MetricBaseline, Mission
from app.schemas.schemas import AlertOut, AlertPatch, AnalysisOut, AstronautCreate, AstronautOut, AstronautPatch, BaselineOut, DashboardSummary, DataSourceOut, MedicalHistoryCreate, MedicalHistoryOut, MedicalHistoryPatch, MeasurementCreate, MeasurementOut, MissionCreate, MissionOut
from app.services.analysis_service import run_analysis
from app.ml_router import registry_for_request

router = APIRouter()

@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)) -> dict:
    db.execute(select(1))
    registry = registry_for_request(request)
    return {
        "status": "ok", "service": "astroguard-api", "database": "connected",
        "models_loaded": [name for name, info in registry["status"].items() if info["loaded"]],
        "models": registry["status"],
        "model_data_origin": registry["data_origin"],
    }

@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    astronauts = list(db.scalars(select(Astronaut).options(joinedload(Astronaut.mission))))
    alert_count = db.scalar(select(func.count(Alert.id)).where(Alert.status != "resolved")) or 0
    review_count = db.scalar(select(func.count(Alert.id)).where(Alert.status == "open")) or 0
    measurement_count = db.scalar(select(func.count(Measurement.id))) or 0
    recent = list(db.scalars(select(Measurement).options(joinedload(Measurement.astronaut)).order_by(Measurement.measured_at.desc()).limit(8)))
    active_alerts = list(db.scalars(select(Alert).options(joinedload(Alert.astronaut)).where(Alert.status != "resolved").order_by(Alert.created_at.desc()).limit(8)))
    mission_name = astronauts[0].mission.name if astronauts and astronauts[0].mission else "No active mission"
    return {
        "astronaut_count": len(astronauts), "measurement_count": measurement_count, "active_alert_count": alert_count,
        "review_count": review_count, "mission_name": mission_name,
        "mission_start_date": astronauts[0].mission.start_date if astronauts and astronauts[0].mission else None,
        "recent_measurements": [{"id": str(m.id), "astronaut_id": str(m.astronaut_id), "astronaut": m.astronaut.callsign, "metric": m.metric, "value": m.value, "unit": m.unit, "measured_at": m.measured_at, "source_type": m.source_type} for m in recent],
        "recent_alerts": [{"id": str(a.id), "astronaut_id": str(a.astronaut_id), "astronaut": a.astronaut.callsign, "title": a.title, "metric": a.metric, "observed_value": a.observed_value, "unit": a.unit, "priority": a.priority, "status": a.status, "created_at": a.created_at} for a in active_alerts],
    }

@router.get("/missions", response_model=list[MissionOut])
def list_missions(db: Session = Depends(get_db)):
    return list(db.scalars(select(Mission).order_by(Mission.name)))

@router.post("/missions", response_model=MissionOut, status_code=201)
def create_mission(payload: MissionCreate, db: Session = Depends(get_db)):
    mission = Mission(**payload.model_dump())
    db.add(mission); db.commit(); db.refresh(mission)
    return mission

@router.get("/data-sources", response_model=list[DataSourceOut])
def list_data_sources(db: Session = Depends(get_db)):
    return list(db.scalars(select(DataSource).order_by(DataSource.is_simulated.desc(), DataSource.name)))

@router.get("/astronauts", response_model=list[AstronautOut])
def list_astronauts(q: str = "", status: str = "", mission_id: UUID | None = None, db: Session = Depends(get_db)):
    stmt = select(Astronaut).options(joinedload(Astronaut.mission)).order_by(Astronaut.callsign)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(Astronaut.full_name.ilike(pattern) | Astronaut.callsign.ilike(pattern))
    if status: stmt = stmt.where(Astronaut.monitoring_status == status)
    if mission_id: stmt = stmt.where(Astronaut.mission_id == mission_id)
    return list(db.scalars(stmt))

@router.post("/astronauts", response_model=AstronautOut, status_code=201)
def create_astronaut(payload: AstronautCreate, db: Session = Depends(get_db)):
    if db.get(Mission, payload.mission_id) is None: raise HTTPException(404, "Mission not found")
    astronaut = Astronaut(**payload.model_dump())
    db.add(astronaut); db.commit()
    return db.scalar(select(Astronaut).options(joinedload(Astronaut.mission)).where(Astronaut.id == astronaut.id))

@router.get("/astronauts/{astronaut_id}", response_model=AstronautOut)
def get_astronaut(astronaut_id: UUID, db: Session = Depends(get_db)):
    astronaut = db.scalar(select(Astronaut).options(joinedload(Astronaut.mission)).where(Astronaut.id == astronaut_id))
    if astronaut is None: raise HTTPException(404, "Astronaut not found")
    return astronaut

@router.patch("/astronauts/{astronaut_id}", response_model=AstronautOut)
def patch_astronaut(astronaut_id: UUID, payload: AstronautPatch, db: Session = Depends(get_db)):
    astronaut = db.scalar(select(Astronaut).options(joinedload(Astronaut.mission)).where(Astronaut.id == astronaut_id))
    if astronaut is None: raise HTTPException(404, "Astronaut not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(astronaut, key, value)
    db.commit(); db.refresh(astronaut)
    return astronaut

@router.get("/astronauts/{astronaut_id}/medical-history", response_model=list[MedicalHistoryOut])
def list_medical_history(astronaut_id: UUID, db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    return list(db.scalars(select(MedicalHistory).where(MedicalHistory.astronaut_id == astronaut_id).order_by(MedicalHistory.recorded_at.desc())))

@router.post("/astronauts/{astronaut_id}/medical-history", response_model=MedicalHistoryOut, status_code=201)
def create_medical_history(astronaut_id: UUID, payload: MedicalHistoryCreate, db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    values = payload.model_dump(exclude={"recorded_at"})
    item = MedicalHistory(astronaut_id=astronaut_id, recorded_at=payload.recorded_at or datetime.now(timezone.utc), **values)
    db.add(item); db.commit(); db.refresh(item)
    return item

@router.patch("/medical-history/{history_id}", response_model=MedicalHistoryOut)
def patch_medical_history(history_id: UUID, payload: MedicalHistoryPatch, db: Session = Depends(get_db)):
    item = db.get(MedicalHistory, history_id)
    if item is None: raise HTTPException(404, "Medical history entry not found")
    update = payload.model_dump(exclude_unset=True)
    for key, value in update.items(): setattr(item, key, value)
    if "verification_status" in update:
        item.reviewed_at = datetime.now(timezone.utc)
        item.reviewed_by = update.get("reviewed_by") or "Medical reviewer"
    db.commit(); db.refresh(item)
    return item

@router.delete("/medical-history/{history_id}", status_code=204)
def delete_medical_history(history_id: UUID, db: Session = Depends(get_db)):
    item = db.get(MedicalHistory, history_id)
    if item is None: raise HTTPException(404, "Medical history entry not found")
    db.delete(item); db.commit()

@router.get("/astronauts/{astronaut_id}/measurements", response_model=list[MeasurementOut])
def list_measurements(astronaut_id: UUID, metric: str = "", limit: int = Query(300, ge=1, le=2000), db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    stmt = select(Measurement).where(Measurement.astronaut_id == astronaut_id).order_by(Measurement.measured_at.desc()).limit(limit)
    if metric: stmt = stmt.where(Measurement.metric == metric)
    return list(db.scalars(stmt))

@router.post("/astronauts/{astronaut_id}/measurements", response_model=MeasurementOut, status_code=201)
def create_measurement(astronaut_id: UUID, payload: MeasurementCreate, db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    measurement = Measurement(astronaut_id=astronaut_id, metric=payload.metric.strip(), value=payload.value, unit=payload.unit.strip(), measured_at=payload.measured_at or datetime.now(timezone.utc), source_type=payload.source_type, symptoms=payload.symptoms, notes=payload.notes)
    db.add(measurement); db.commit(); db.refresh(measurement)
    return measurement

@router.get("/astronauts/{astronaut_id}/baseline", response_model=list[BaselineOut])
def list_baselines(astronaut_id: UUID, db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    return list(db.scalars(select(MetricBaseline).where(MetricBaseline.astronaut_id == astronaut_id).order_by(MetricBaseline.metric)))

@router.post("/astronauts/{astronaut_id}/analysis", response_model=AnalysisOut)
def create_analysis(astronaut_id: UUID, db: Session = Depends(get_db)):
    astronaut = db.get(Astronaut, astronaut_id)
    if astronaut is None: raise HTTPException(404, "Astronaut not found")
    return run_analysis(db, astronaut)

@router.get("/astronauts/{astronaut_id}/analysis", response_model=list[AnalysisOut])
def list_analysis(astronaut_id: UUID, db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    return list(db.scalars(select(AnalysisResult).where(AnalysisResult.astronaut_id == astronaut_id).order_by(AnalysisResult.created_at.desc()).limit(50)))

@router.get("/astronauts/{astronaut_id}/analysis/latest", response_model=AnalysisOut)
def latest_analysis(astronaut_id: UUID, db: Session = Depends(get_db)):
    latest = db.scalar(select(AnalysisResult).where(AnalysisResult.astronaut_id == astronaut_id).order_by(AnalysisResult.created_at.desc()).limit(1))
    if latest is None: raise HTTPException(404, "No analysis available")
    return latest

@router.get("/astronauts/{astronaut_id}/alerts", response_model=list[AlertOut])
def astronaut_alerts(astronaut_id: UUID, db: Session = Depends(get_db)):
    if db.get(Astronaut, astronaut_id) is None: raise HTTPException(404, "Astronaut not found")
    return list(db.scalars(select(Alert).where(Alert.astronaut_id == astronaut_id).order_by(Alert.created_at.desc())))

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(status: str = "", priority: str = "", db: Session = Depends(get_db)):
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if status: stmt = stmt.where(Alert.status == status)
    if priority: stmt = stmt.where(Alert.priority == priority)
    return list(db.scalars(stmt))

@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: UUID, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if alert is None: raise HTTPException(404, "Alert not found")
    return alert

@router.patch("/alerts/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: UUID, payload: AlertPatch, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if alert is None: raise HTTPException(404, "Alert not found")
    update = payload.model_dump(exclude_unset=True)
    if "status" in update and update["status"] not in {"open", "acknowledged", "resolved"}:
        raise HTTPException(422, "Status must be open, acknowledged, or resolved")
    for key, value in update.items(): setattr(alert, key, value)
    if update.get("status") in {"acknowledged", "resolved"}:
        alert.reviewed_at = datetime.now(timezone.utc)
        if not alert.reviewed_by: alert.reviewed_by = "Medical reviewer"
    db.commit(); db.refresh(alert)
    return alert
