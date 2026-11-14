from collections.abc import Sequence
from math import isfinite
import numpy as np

def robust_band(values: Sequence[float], *, floor: float) -> tuple[float, float, float]:
    """Median and robust demo band; descriptive only, not a clinical interval."""
    data = np.asarray(list(values), dtype=float)
    data = data[np.isfinite(data)]
    if data.size == 0:
        raise ValueError("At least one finite observation is required to form a personal band")
    if not isfinite(floor) or floor <= 0:
        raise ValueError("The robust spread floor must be a positive finite number")
    median = float(np.median(data))
    mad = float(np.median(np.abs(data - median)))
    spread = max(1.4826 * mad, floor)
    return median, median - 3.0 * spread, median + 3.0 * spread
