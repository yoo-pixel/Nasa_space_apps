from collections.abc import Iterable
import math

def clean_values(values: Iterable[float]) -> list[float]:
    """Drop non-finite values before descriptive analysis."""
    return [float(value) for value in values if math.isfinite(float(value))]
