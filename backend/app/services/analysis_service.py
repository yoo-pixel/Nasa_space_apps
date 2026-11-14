from sqlalchemy import select
from sqlalchemy.orm import Session
from app.ml.inference import analyze_health
from app.models import Alert, AnalysisResult, Astronaut, Measurement, MetricBaseline

def run_analysis(db: Session, astronaut: Astronaut, measurements: list[Measurement] | None = None) -> AnalysisResult:
    measurements = measurements or list(db.scalars(select(Measurement).where(Measurement.astronaut_id == astronaut.id).order_by(Measurement.measured_at.desc()).limit(50)))
    baselines = {
        row.metric: {
            "median": row.median,
            "lower_bound": row.lower_bound,
            "upper_bound": row.upper_bound,
            "sample_count": row.sample_count,
            "method": row.method,
            "unit": row.unit,
        }
        for row in db.scalars(select(MetricBaseline).where(MetricBaseline.astronaut_id == astronaut.id))
    }
    observed_rows = [
        {
            "measurement_id": str(item.id),
            "metric": item.metric,
            "value": item.value,
            "unit": item.unit,
            "measured_at": item.measured_at,
            "source_type": item.source_type,
        }
        for item in measurements
    ]
    result = analyze_health(str(astronaut.id), observed_rows, baselines)
    analysis = AnalysisResult(astronaut_id=astronaut.id, model_name=result["model_name"], model_version=result["model_version"], summary=result["summary"], findings=result["findings"], anomaly_score=result["anomaly_score"], needs_review=result["needs_review"])
    db.add(analysis)
    db.flush()
    for finding in result["findings"]:
        if not finding["is_flagged"]:
            continue
        measurement = next((m for m in measurements if str(m.id) == finding.get("measurement_id")), None)
        if measurement is None:
            continue
        existing = db.scalar(select(Alert).where(Alert.measurement_id == measurement.id, Alert.status != "resolved"))
        if existing is None:
            db.add(Alert(astronaut_id=astronaut.id, analysis_id=analysis.id, measurement_id=measurement.id, title=f"{finding['metric']} outside personal comparison band", metric=finding["metric"], observed_value=finding["value"], unit=finding["unit"], baseline_value=finding["baseline"], explanation=finding["explanation"], priority="review", status="open"))
    db.commit()
    db.refresh(analysis)
    return analysis
