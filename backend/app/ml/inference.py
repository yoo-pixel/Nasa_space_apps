"""Descriptive, person-specific review evidence from already-recorded data.

This module intentionally has no diagnostic classifier or future forecaster.
It produces observations for a qualified clinician to interpret in mission
context.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import isfinite
from statistics import median

from app.ml.anomaly_detection import compare_to_baseline
from app.ml.model import MODEL_NAME, MODEL_VERSION

REVIEW_WINDOW_DAYS = 14


def _as_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _observed_context(
    measurement: dict,
    measurements: list[dict],
    baseline: dict,
) -> dict:
    """Summarize past observations only; slope describes history, not a forecast."""
    anchor = _as_utc(measurement.get("measured_at"))
    if anchor is None:
        return {
            "status": "unavailable",
            "reason": "The measurement has no usable timestamp.",
            "window_days": REVIEW_WINDOW_DAYS,
            "observation_count": 0,
            "distinct_days": 0,
            "observed_slope_per_day": None,
            "out_of_band_days": None,
        }

    start = anchor - timedelta(days=REVIEW_WINDOW_DAYS)
    rows: list[tuple[datetime, float]] = []
    sources: set[str] = set()
    for row in measurements:
        if row.get("metric") != measurement.get("metric") or row.get("unit") != measurement.get("unit"):
            continue
        stamp = _as_utc(row.get("measured_at"))
        if stamp is None or stamp < start or stamp > anchor:
            continue
        try:
            value = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue
        if not isfinite(value):
            continue
        rows.append((stamp, value))
        source = str(row.get("source_type") or "unspecified")
        sources.add(source)

    rows.sort(key=lambda item: item[0])
    by_day: dict[str, list[float]] = defaultdict(list)
    for stamp, value in rows:
        by_day[stamp.date().isoformat()].append(value)
    days = sorted(by_day)
    daily_values = [median(by_day[day]) for day in days]

    slope: float | None = None
    out_of_band_days: int | None = None
    reason = "At least three distinct observation days are needed for a descriptive slope."
    if len(days) >= 3:
        x = [(datetime.fromisoformat(day) - datetime.fromisoformat(days[0])).days for day in days]
        x_mean = sum(x) / len(x)
        y_mean = sum(daily_values) / len(daily_values)
        denominator = sum((value - x_mean) ** 2 for value in x)
        if denominator > 0:
            slope = sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(x, daily_values)) / denominator
            reason = "Slope summarizes observed daily medians only; it is not extrapolated."
        low = float(baseline["lower_bound"])
        high = float(baseline["upper_bound"])
        out_of_band_days = sum(value < low or value > high for value in daily_values)

    first_to_last_delta = daily_values[-1] - daily_values[0] if len(daily_values) >= 2 else None
    return {
        "status": "available" if rows else "unavailable",
        "window_days": REVIEW_WINDOW_DAYS,
        "observation_count": len(rows),
        "distinct_days": len(days),
        "window_start_utc": start.isoformat(),
        "window_end_utc": anchor.isoformat(),
        "first_to_last_daily_median_delta": round(first_to_last_delta, 4) if first_to_last_delta is not None else None,
        "observed_slope_per_day": round(slope, 5) if slope is not None else None,
        "out_of_band_days": out_of_band_days,
        "source_types": sorted(sources),
        "interpretation": reason,
        "completeness_note": "This context uses records supplied to the analysis; ingestion gaps can make the window incomplete.",
    }


def analyze_health(
    astronaut_id: str,
    measurements: list[dict],
    baselines: dict[str, dict],
    medical_history: list[dict] | None = None,
) -> dict:
    """Return personal-band findings and retrospective context for human review."""
    findings = []
    for measurement in measurements:
        baseline = baselines.get(measurement["metric"])
        if not baseline:
            continue
        value = float(measurement["value"])
        if not isfinite(value):
            continue
        finding = compare_to_baseline(
            measurement["metric"], value, measurement["unit"], baseline
        ).__dict__
        finding["measured_at"] = (
            measurement.get("measured_at").isoformat()
            if isinstance(measurement.get("measured_at"), datetime)
            else measurement.get("measured_at")
        )
        finding["source_type"] = measurement.get("source_type", "unspecified")
        finding["measurement_id"] = measurement.get("measurement_id")
        finding["observed_context_14d"] = _observed_context(measurement, measurements, baseline)
        findings.append(finding)

    flagged = [finding for finding in findings if finding["is_flagged"]]
    if flagged:
        summary = (
            f"{len(flagged)} observation(s) fell outside the stored personal comparison band. "
            "A qualified clinician must interpret these findings with the source record and mission context; "
            "this analysis does not diagnose or estimate future health."
        )
    else:
        summary = (
            "No analyzed observation fell outside the stored personal comparison band. "
            "This is not medical clearance and does not rule out a health concern."
        )

    return {
        "astronaut_id": astronaut_id,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "summary": summary,
        "findings": findings,
        "anomaly_score": max((finding["anomaly_score"] for finding in findings), default=0.0),
        "anomaly_score_interpretation": "Maximum capped distance beyond a stored personal band; not a probability or clinical severity score.",
        "needs_review": bool(flagged),
        "medical_history_available": bool(medical_history),
        "medical_history_considered": False,
        "human_review_required": bool(flagged),
        "clinical_estimate": None,
        "clinical_estimate_note": "Only a qualified medical reviewer can provide a clinical estimate.",
    }
