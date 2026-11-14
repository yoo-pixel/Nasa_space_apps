import math
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.ml.baseline import robust_band
from app.models import Astronaut, DataSource, MedicalHistory, Measurement, MetricBaseline, Mission, User

METRICS = {
    "heart_rate": ("bpm", 67.0, 5.0),
    "spo2": ("%", 97.0, 0.65),
    "temperature": ("°C", 36.7, 0.15),
    "systolic_bp": ("mmHg", 116.0, 3.0),
    "diastolic_bp": ("mmHg", 76.0, 2.5),
}
CREW = [
    ("Dr. Amara Okafor", "NOVA", "Flight surgeon", "#198D6D", "stable"),
    ("Elias Park", "ORBIT", "Mission specialist", "#1F75A5", "stable"),
    ("Mina Alvarez", "SOL", "Pilot", "#258694", "monitoring"),
    ("Jonah Reed", "ATLAS", "Flight engineer", "#2D43AA", "stable"),
    ("Leila Haddad", "COMET", "Mission specialist", "#DB968C", "review"),
]

def seed_demo_data() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Astronaut.id).limit(1)) is not None: return
        random.seed(24)
        now = datetime.now(timezone.utc)
        mission = Mission(name="Asteria-04", status="active", destination="Low Earth Orbit", start_date=now-timedelta(days=18), description="Simulated orbital research mission for application demonstration.")
        demo_source = DataSource(name="AstroGuard synthetic demonstration set", organization="AstroGuard", description="Programmatically generated sample measurements for local development. Not NASA research data.", dataset_version="demo-1.0", is_simulated=True, status="loaded")
        nasa_source = DataSource(name="NASA Open Science Data Repository (OSDR)", organization="NASA", description="Broad OSDR study ingestion is not connected. A separate read-only RadLab ISS environment feed is available; no OSDR biology studies are loaded into astronaut health records.", dataset_version="not loaded", url="https://osdr.nasa.gov/", is_simulated=False, status="not_connected")
        db.add_all([mission, demo_source, nasa_source, User(name="Demo Medical Reviewer", email="reviewer@astroguard.local", role="medical_reviewer")])
        db.flush()
        for index, (name, callsign, role, color, status) in enumerate(CREW):
            astronaut = Astronaut(mission_id=mission.id, full_name=name, callsign=callsign, role=role, nationality=["US", "DE", "EG", "CA", "JP"][index], avatar_color=color, monitoring_status=status, notes="Simulated crew profile for interface demonstration.")
            db.add(astronaut); db.flush()
            db.add(MedicalHistory(astronaut_id=astronaut.id, category="Preflight review", summary="Synthetic demo record: routine preflight review completed. No real personal medical data.", recorded_at=now-timedelta(days=30), recorded_by="Demo medical team"))
            personal_rows = []
            for day in range(18, 0, -1):
                stamp = now-timedelta(days=day)
                for metric_index, (metric, (unit, center, noise)) in enumerate(METRICS.items()):
                    wobble = math.sin((day+index*3+metric_index)/4)*noise*0.35
                    value = center+wobble+random.uniform(-noise, noise)
                    personal_rows.append((metric, value, unit, stamp+timedelta(minutes=metric_index*3)))
            for metric, value, unit, stamp in personal_rows:
                db.add(Measurement(astronaut_id=astronaut.id, data_source_id=demo_source.id, metric=metric, value=round(value, 1), unit=unit, measured_at=stamp, source_type="simulated", symptoms=[], notes="Synthetic demonstration measurement"))
            db.flush()
            for metric, (unit, _, noise) in METRICS.items():
                values = [value for metric_name, value, _, _ in personal_rows if metric_name == metric]
                median, low, high = robust_band(values, floor=max(noise*1.4, 0.1))
                db.add(MetricBaseline(astronaut_id=astronaut.id, metric=metric, unit=unit, median=round(median,1), lower_bound=round(low,1), upper_bound=round(high,1), sample_count=len(values), method="Personal synthetic history · median ± 3 robust spreads", updated_at=now))
        db.flush()
        for callsign, metric, value, unit, days_ago in [("NOVA","heart_rate",92.0,"bpm",0.12),("SOL","spo2",92.0,"%",0.3),("COMET","temperature",37.6,"°C",0.6)]:
            astronaut = db.scalar(select(Astronaut).where(Astronaut.callsign == callsign))
            source = db.scalar(select(DataSource).where(DataSource.name == "AstroGuard synthetic demonstration set"))
            db.add(Measurement(astronaut_id=astronaut.id, data_source_id=source.id, metric=metric, value=value, unit=unit, measured_at=now-timedelta(days=days_ago), source_type="simulated", symptoms=[], notes="Synthetic outlier included to demonstrate human review."))
        db.commit()
        from app.services.analysis_service import run_analysis
        for member in db.scalars(select(Astronaut)).all():
            run_analysis(db, member)
