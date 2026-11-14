from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.nasa_radlab import get_radlab_records

router = APIRouter(prefix="/research", tags=["NASA research data"])


@router.get("/radlab")
def radlab_feed(
    start: datetime = Query(..., description="UTC start time, ISO 8601"),
    end: datetime = Query(..., description="UTC end time, ISO 8601; maximum 24 hours after start"),
    instrument: Literal["DosTel1", "REM-Lid", "Lidal"] = "DosTel1",
):
    try:
        return get_radlab_records(start, end, instrument)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
