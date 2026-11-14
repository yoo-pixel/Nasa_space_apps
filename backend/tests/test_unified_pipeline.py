from __future__ import annotations

import pandas as pd
import pytest

from ml.research_data import local_forecast_request, normalize_measurements


def test_long_measurements_normalize_with_units_and_unknowns_preserved() -> None:
    daily = normalize_measurements()
    assert daily["astronaut_id"].nunique() == 3
    assert daily["is_simulated"].all()

    person = daily[daily.astronaut_id == "AG-001"].set_index("mission_day")
    assert -13 in person.index and 0 in person.index and 45 in person.index
    assert person.loc[person.index <= 0, "resting_hr_bpm"].notna().any()
    assert pd.notna(person.loc[14, "wbc_count_k_ul"])
    assert pd.notna(person.loc[14, "daily_rad_rate_msv"])
    assert person.loc[1, "cumulative_rad_msv"] == pytest.approx(person.loc[1, "daily_rad_rate_msv"])
    assert person.loc[-19, "bmd_drift_pct"] == pytest.approx(0.0)
    # This source has no in-mission DXA readings, so it cannot support a
    # measured mission bone-drift value.
    assert pd.isna(person.loc[28, "bmd_drift_pct"])
    # The source does not measure these model inputs; they must remain missing.
    assert pd.isna(person.loc[20, "cabin_co2_mmhg"])
    assert pd.isna(person.loc[20, "nlr_ratio"])
    assert pd.isna(person.loc[20, "winscat_rt_ms"])


def test_local_forecast_request_builds_consecutive_earth_and_mission_windows() -> None:
    request, quality = local_forecast_request("AG-002", 20)
    assert len(request["earth_baseline"]) == 14
    assert len(request["mission_telemetry"]) == 14
    assert request["mission_day"] == 20
    assert request["data_origin"] == "repository_synthetic_long_measurements"
    assert quality["is_simulated"] is True
    assert "vo2_max_earth" in quality["pre_medical_fields_imputed"]
    assert request["mission_telemetry"][-1]["cabin_co2_mmhg"] is None


def test_local_forecast_request_rejects_unknown_astronaut_and_day() -> None:
    with pytest.raises(ValueError, match="Unknown astronaut_id"):
        local_forecast_request("REAL-001", 20)
    with pytest.raises(ValueError, match="mission_day must be between"):
        local_forecast_request("AG-001", 46)
