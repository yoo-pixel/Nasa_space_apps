from dataclasses import dataclass
from math import isfinite

@dataclass
class Finding:
    metric: str
    value: float
    unit: str
    baseline: float
    lower_bound: float
    upper_bound: float
    anomaly_score: float
    is_flagged: bool
    explanation: str
    deviation_from_baseline: float
    deviation_percent: float | None
    direction: str
    baseline_sample_count: int
    baseline_method: str
    baseline_context: str
    score_interpretation: str

def compare_to_baseline(metric: str, value: float, unit: str, baseline: dict) -> Finding:
    median = float(baseline["median"])
    low, high = float(baseline["lower_bound"]), float(baseline["upper_bound"])
    if not all(isfinite(number) for number in (value, median, low, high)):
        raise ValueError("Measurement and personal baseline values must be finite")
    if low > median or median > high:
        raise ValueError("Personal baseline bounds must contain the median")

    width = max(high - low, 1e-9)
    outside = value < low or value > high
    distance = (low - value) / width if value < low else ((value - high) / width if value > high else 0.0)
    score = min(1.0, max(0.0, distance))
    method = str(baseline.get("method", ""))
    normalized_method = method.lower()
    if "synthetic" in normalized_method or "demo" in normalized_method:
        context = "synthetic_demo"
    elif "observed" in normalized_method:
        context = "personal_observations"
    else:
        context = "unspecified"
    delta = value - median
    percent_delta = (delta / abs(median)) * 100.0 if median != 0 else None
    direction = "above" if delta > 0 else "below" if delta < 0 else "at_median"
    explanation = (
        f"{metric} is {value:g} {unit}, outside this astronaut's stored personal comparison band "
        f"({low:g}–{high:g} {unit}; median {median:g} {unit}). This is a review flag, not a clinical threshold."
        if outside else f"{metric} is {value:g} {unit}, within this astronaut's stored personal comparison band "
        f"({low:g}–{high:g} {unit}). A within-band result does not establish medical clearance."
    )
    return Finding(
        metric=metric,
        value=value,
        unit=unit,
        baseline=median,
        lower_bound=low,
        upper_bound=high,
        anomaly_score=score,
        is_flagged=outside,
        explanation=explanation,
        deviation_from_baseline=delta,
        deviation_percent=percent_delta,
        direction=direction,
        baseline_sample_count=int(baseline.get("sample_count", 0)),
        baseline_method=method,
        baseline_context=context,
        score_interpretation="Capped distance beyond the stored personal band; not a probability or clinical severity score.",
    )
