"""Read-only access to NASA OSDR's public RadLab environmental telemetry API."""

import json
from datetime import datetime, timezone
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RADLAB_API = "https://visualization.osdr.nasa.gov/radlab/api/"
ALLOWED_INSTRUMENTS = {"DosTel1", "REM-Lid", "Lidal"}
FIELDS = (
    "timestamp", "instrument_id", "absorbed_dose_rate", "dose_equivalent_rate",
    "latitude", "longitude", "altitude", "spacecraft",
)


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def get_radlab_records(start: datetime, end: datetime, instrument: str) -> dict:
    if instrument not in ALLOWED_INSTRUMENTS:
        raise ValueError("Choose one of the supported ISS instruments.")
    start, end = _utc_naive(start), _utc_naive(end)
    duration = end - start
    if duration.total_seconds() <= 0:
        raise ValueError("The end time must be after the start time.")
    if duration.total_seconds() > 24 * 60 * 60:
        raise ValueError("Choose a time window of 24 hours or less.")

    params = [
        ("spacecraft", "ISS"),
        ("instrument", instrument),
        ("timestamp>", start.isoformat(timespec="minutes")),
        ("timestamp<", end.isoformat(timespec="minutes")),
        *((field, "") for field in FIELDS),
        ("format", "json"),
    ]
    url = RADLAB_API + "?" + urlencode(params)
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "AstroGuard/0.1 research prototype"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"NASA RadLab returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not retrieve the NASA RadLab feed right now.") from exc

    columns = payload.get("columns", [])
    raw_rows = payload.get("data", [])
    rows = []
    for raw in raw_rows[:1500]:
        if not isinstance(raw, list):
            continue
        item = dict(zip(columns, raw))
        if item.get("spacecraft") != "ISS":
            continue
        clean = {}
        for field in FIELDS:
            value = item.get(field)
            if field in {"absorbed_dose_rate", "dose_equivalent_rate", "latitude", "longitude", "altitude"}:
                try:
                    number = float(value) if value is not None else None
                    clean[field] = number if number is not None and isfinite(number) else None
                except (TypeError, ValueError):
                    clean[field] = None
            else:
                clean[field] = value
        rows.append(clean)

    return {
        "source": "NASA OSDR RadLab",
        "source_url": url,
        "spacecraft": "ISS",
        "instrument": instrument,
        "start": start.isoformat(timespec="minutes") + "Z",
        "end": end.isoformat(timespec="minutes") + "Z",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "units": {"absorbed_dose_rate": "µGy/hour", "dose_equivalent_rate": "µSv/hour", "altitude": "km", "latitude": "degrees", "longitude": "degrees"},
        "rows": rows,
        "truncated": len(raw_rows) > len(rows),
    }
