"""Standalone smoke checks: python backend/ml/test_ml.py"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import joblib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from data_loader import build_synthetic_corpus  # noqa: E402
from train_ml import (  # noqa: E402
    MODEL_DIR,
    _feature_window,
    build_windows,
    detect_sudden_changes,
    explain_and_recommend,
    forecast_trajectory,
    train_all,
)


class PipelineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = build_synthetic_corpus(astronauts=8, mission_days=30, seed=42)
        required = {
            "heart": MODEL_DIR / "heart_model.pkl", "nerve": MODEL_DIR / "nerve_model.pkl",
            "immune": MODEL_DIR / "immune_model.pkl", "bone": MODEL_DIR / "bone_model.pkl",
            "anomaly": MODEL_DIR / "anomaly_detector.pkl",
        }
        cls.paths = required if all(path.exists() for path in required.values()) else train_all(cls.data)

    def test_day_one_uses_earth_padding_without_future_rows(self) -> None:
        person = self.data[self.data.astronaut_id == "SIM-001"]
        features = _feature_window(person, 1)
        self.assertEqual(features["mission_day"], 1.0)
        self.assertTrue(all(name in features for name in ("resting_hr_bpm__delta_pct", "resting_hr_bpm__z_drift")))
        truncated = person[person.mission_day <= 1]
        self.assertEqual(features, _feature_window(truncated, 1))

    def test_day_twenty_forecasts_seven_horizons(self) -> None:
        person = self.data[self.data.astronaut_id == "SIM-001"]
        feature_row = _feature_window(person, 20)
        artifact = joblib.load(self.paths["heart"])
        forecast = forecast_trajectory(artifact, feature_row)
        self.assertEqual(set(forecast), {f"day_{n}" for n in range(1, 8)})
        self.assertIn("resting_hr_bpm", forecast["day_1"])

    def test_spikes_are_flagged(self) -> None:
        artifact = joblib.load(self.paths["anomaly"])
        result = detect_sudden_changes(
            artifact,
            {"cabin_co2_mmhg": 4.0, "sbp_mmhg": 90.0, "daily_rad_rate_msv": 6.0},
            {"sbp_mmhg": 110.0},
        )
        self.assertTrue(result["anomaly_detected"])
        self.assertEqual(len(result["demo_triggers"]), 3)

    def test_countermeasure_output_is_review_labeled(self) -> None:
        result = explain_and_recommend({"cabin_co2_mmhg": 3.2, "sleep_duration_hrs": 5.8, "resting_hr_bpm__z_drift": 2.2})
        self.assertEqual(result["primary_observed_driver"], "resting_hr_bpm__z_drift")
        self.assertTrue(result["ranked_scenarios_for_clinician_review"])
        self.assertIn("not an intervention recommendation", result["scenario_note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
