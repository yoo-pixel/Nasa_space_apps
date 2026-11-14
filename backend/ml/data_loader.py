"""OSDR/NLSP acquisition and clearly synthetic pipeline demo data.

Downloaded human-study files are preserved as raw research inputs. They are
never silently converted into daily crew telemetry or clinical labels.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests

LOGGER = logging.getLogger("astroguard.ml.data_loader")
ROOT = Path(__file__).resolve().parents[1]
RAW_OSDR = ROOT / "data" / "raw" / "osdr"
RAW_NLSP = ROOT / "data" / "raw" / "nlsp"
PROCESSED = ROOT / "data" / "processed"
OSDR_STUDIES = {"569": "OSD-569", "575": "OSD-575", "656": "OSD-656", "571": "OSD-571"}
NLSP_IDS = ("BRSMAct", "MR001G", "BEDREST0543", "MR085G", "BRSMpQCT", "BRSMRF")

SYSTEM_FIELDS = {
    "heart": ["resting_hr_bpm", "hrv_rmssd_ms", "sbp_mmhg", "dbp_mmhg", "pulse_pressure_mmhg"],
    "nerve": ["sleep_duration_hrs", "sleep_efficiency_pct", "winscat_rt_ms", "winscat_accuracy_pct"],
    "immune": ["cumulative_rad_msv", "daily_rad_rate_msv", "wbc_count_k_ul", "nlr_ratio"],
    "bone": ["bmd_drift_pct", "serum_calcium_mg_dl", "urinary_calcium_mg_day", "ared_exercise_load_pct"],
}
VITAL_COLUMNS = [field for fields in SYSTEM_FIELDS.values() for field in fields]
ENVIRONMENT_COLUMNS = ["gravity_g", "cabin_co2_mmhg", "cabin_po2_mmhg", "cabin_pressure_psi"]
PREMED_COLUMNS = ["prior_arrhythmia_flag", "vo2_max_earth", "baseline_t_score", "baseline_optic_nerve_mm"]


def _candidate_files(payload: Any) -> list[tuple[str, str]]:
    """Walk the OSDR response without assuming one specific JSON envelope."""
    found: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        remote = payload.get("remote_url") or payload.get("download_url") or payload.get("url")
        name = payload.get("file_name") or payload.get("filename") or payload.get("name")
        if isinstance(remote, str) and isinstance(name, str):
            if Path(name).suffix.lower() in {".csv", ".tsv", ".txt"}:
                found.append((name, remote))
        for value in payload.values():
            found.extend(_candidate_files(value))
    elif isinstance(payload, list):
        for value in payload:
            found.extend(_candidate_files(value))
    return found


def download_osdr(timeout: int = 15) -> list[dict[str, str]]:
    RAW_OSDR.mkdir(parents=True, exist_ok=True)
    status: list[dict[str, str]] = []
    session = requests.Session()
    for number, accession in OSDR_STUDIES.items():
        endpoint = f"https://osdr.nasa.gov/osdr/data/osd/files/{number}"
        try:
            response = session.get(endpoint, timeout=timeout)
            response.raise_for_status()
            candidates = _candidate_files(response.json())
            downloaded = 0
            for filename, remote in candidates:
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name)
                target = RAW_OSDR / f"{accession}_{safe_name}"
                if target.exists() and target.stat().st_size:
                    continue
                url = remote if remote.startswith("http") else urljoin("https://osdr.nasa.gov", remote)
                file_response = session.get(url, timeout=timeout, stream=True)
                file_response.raise_for_status()
                temp = target.with_suffix(target.suffix + ".part")
                with temp.open("wb") as handle:
                    for chunk in file_response.iter_content(1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                temp.replace(target)
                downloaded += 1
            status.append({"study": accession, "status": "ok", "new_files": str(downloaded)})
            LOGGER.info("%s: %s new tabular file(s)", accession, downloaded)
        except (requests.RequestException, ValueError, OSError) as exc:
            status.append({"study": accession, "status": "offline_or_unavailable", "detail": str(exc)})
            LOGGER.warning("%s unavailable; using cached/local files only: %s", accession, exc)
    return status


def discover_nlsp() -> list[dict[str, Any]]:
    RAW_NLSP.mkdir(parents=True, exist_ok=True)
    found = []
    for path in sorted(RAW_NLSP.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".tsv"}:
            continue
        matched = [study_id for study_id in NLSP_IDS if study_id.lower() in path.name.lower()]
        if not matched:
            continue
        try:
            frame = pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else ",", nrows=5)
            found.append({"path": str(path), "experiment_ids": matched, "columns": list(map(str, frame.columns))})
        except Exception as exc:  # malformed manual exports remain untouched
            LOGGER.warning("Could not inspect %s: %s", path.name, exc)
    return found


def _clip(rng: np.random.Generator, mean: float, sd: float, low: float, high: float) -> float:
    return float(np.clip(rng.normal(mean, sd), low, high))


def build_synthetic_corpus(astronauts: int = 30, mission_days: int = 70, seed: int = 2026) -> pd.DataFrame:
    """Build a labeled *synthetic demo benchmark*, never NASA/clinical evidence."""
    rng = np.random.default_rng(seed)
    records: list[dict[str, Any]] = []
    for person in range(astronauts):
        person_id = f"SIM-{person + 1:03d}"
        earth = {
            "resting_hr_bpm": _clip(rng, 68, 5, 50, 85),
            "hrv_rmssd_ms": _clip(rng, 58, 12, 25, 100),
            "sbp_mmhg": _clip(rng, 116, 8, 95, 140),
            "dbp_mmhg": _clip(rng, 76, 6, 55, 95),
            "sleep_duration_hrs": _clip(rng, 7.5, 0.45, 6, 9),
            "sleep_efficiency_pct": _clip(rng, 88, 4, 75, 98),
            "winscat_rt_ms": _clip(rng, 500, 45, 350, 700),
            "winscat_accuracy_pct": _clip(rng, 94, 3, 82, 100),
            "wbc_count_k_ul": _clip(rng, 6.5, 1, 3.5, 11),
            "nlr_ratio": _clip(rng, 1.8, 0.45, 0.6, 3.5),
            "serum_calcium_mg_dl": _clip(rng, 9.4, 0.35, 8, 11),
            "urinary_calcium_mg_day": _clip(rng, 180, 35, 60, 300),
        }
        flags = {
            "prior_arrhythmia_flag": bool(rng.random() < 0.12),
            "vo2_max_earth": _clip(rng, 48, 9, 25, 75),
            "baseline_t_score": _clip(rng, -0.2, 0.65, -2.2, 1.5),
            "baseline_optic_nerve_mm": _clip(rng, 3.0, 0.25, 2.3, 3.8),
        }
        # Synthetic Earth baseline rows (15 points, days -14 through 0).
        for day in range(-14, 1):
            row = {"astronaut_id": person_id, "mission_day": day, "data_origin": "synthetic_demo", "is_baseline": True}
            row.update(flags)
            row.update({key: 1.0 for key in ["gravity_g"]})
            row.update({"cabin_co2_mmhg": 0.0, "cabin_po2_mmhg": 159.0, "cabin_pressure_psi": 14.7})
            jitter = lambda key, sd: float(rng.normal(earth[key], sd))
            row.update({
                "resting_hr_bpm": jitter("resting_hr_bpm", 2.0), "hrv_rmssd_ms": jitter("hrv_rmssd_ms", 4.0),
                "sbp_mmhg": jitter("sbp_mmhg", 3.0), "dbp_mmhg": jitter("dbp_mmhg", 2.0),
                "sleep_duration_hrs": jitter("sleep_duration_hrs", 0.2), "sleep_efficiency_pct": jitter("sleep_efficiency_pct", 1.5),
                "winscat_rt_ms": jitter("winscat_rt_ms", 15), "winscat_accuracy_pct": jitter("winscat_accuracy_pct", 1.0),
                "cumulative_rad_msv": 0.0, "daily_rad_rate_msv": 0.0, "wbc_count_k_ul": jitter("wbc_count_k_ul", 0.2),
                "nlr_ratio": jitter("nlr_ratio", 0.12), "bmd_drift_pct": 0.0,
                "serum_calcium_mg_dl": jitter("serum_calcium_mg_dl", 0.08), "urinary_calcium_mg_day": jitter("urinary_calcium_mg_day", 10),
                "ared_exercise_load_pct": 100.0,
            })
            row["pulse_pressure_mmhg"] = row["sbp_mmhg"] - row["dbp_mmhg"]
            records.append(row)

        cumulative_rad = 0.0
        for day in range(1, mission_days + 1):
            # Each astronaut experiences a mission regime, with scenario mix across the cohort.
            gravity = (0.0, 0.16, 0.38, 1.0)[person % 4]
            co2 = _clip(rng, 1.8 + (0.45 if day % 19 in range(14, 19) else 0), 0.25, 0.8, 4.2)
            po2 = _clip(rng, 151, 4, 130, 165)
            pressure = _clip(rng, 14.6, 0.18, 10.5, 15.0)
            daily_rad = _clip(rng, 0.65, 0.18, 0.1, 1.4)
            cumulative_rad += daily_rad
            g_shift = (1.0 - gravity) * (1 - np.exp(-day / 10))
            sleep_debt = max(0.0, (7.5 - earth["sleep_duration_hrs"]) * day / 14)
            hr = earth["resting_hr_bpm"] + 5.0 * g_shift + max(0.0, co2 - 2.2) * 2.0 + rng.normal(0, 2.5)
            sbp = earth["sbp_mmhg"] - 5.0 * g_shift + rng.normal(0, 3.0)
            dbp = earth["dbp_mmhg"] - 2.0 * g_shift + rng.normal(0, 2.0)
            row = {"astronaut_id": person_id, "mission_day": day, "data_origin": "synthetic_demo", "is_baseline": False}
            row.update(flags)
            row.update({
                "gravity_g": gravity, "cabin_co2_mmhg": co2, "cabin_po2_mmhg": po2, "cabin_pressure_psi": pressure,
                "resting_hr_bpm": hr, "hrv_rmssd_ms": max(15.0, earth["hrv_rmssd_ms"] - 8 * g_shift + rng.normal(0, 4)),
                "sbp_mmhg": sbp, "dbp_mmhg": dbp, "pulse_pressure_mmhg": sbp - dbp,
                "sleep_duration_hrs": max(4.5, earth["sleep_duration_hrs"] - 0.4 * g_shift + rng.normal(0, 0.3)),
                "sleep_efficiency_pct": np.clip(earth["sleep_efficiency_pct"] - 5 * g_shift + rng.normal(0, 2), 60, 98),
                "winscat_rt_ms": earth["winscat_rt_ms"] * (1 + 0.04 * g_shift + max(0, co2 - 2.5) * 0.02) + rng.normal(0, 18),
                "winscat_accuracy_pct": np.clip(earth["winscat_accuracy_pct"] - 3 * g_shift + rng.normal(0, 1.2), 70, 100),
                "cumulative_rad_msv": cumulative_rad, "daily_rad_rate_msv": daily_rad,
                "wbc_count_k_ul": max(2.5, earth["wbc_count_k_ul"] - 0.35 * g_shift + rng.normal(0, 0.25)),
                "nlr_ratio": max(0.4, earth["nlr_ratio"] + 0.4 * g_shift + rng.normal(0, 0.15)),
                "bmd_drift_pct": -0.018 * day * g_shift + rng.normal(0, 0.04),
                "serum_calcium_mg_dl": max(7.5, earth["serum_calcium_mg_dl"] + 0.2 * g_shift + rng.normal(0, 0.12)),
                "urinary_calcium_mg_day": max(20, earth["urinary_calcium_mg_day"] + 45 * g_shift + rng.normal(0, 15)),
                "ared_exercise_load_pct": np.clip(90 - 10 * g_shift + rng.normal(0, 7), 35, 110),
                "sleep_debt_hrs_demo": sleep_debt,
            })
            records.append(row)
    return pd.DataFrame.from_records(records)


def write_manifest(files: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({"path": str(path), "sha256": digest, "retrieved_at_utc": datetime.now(timezone.utc).isoformat()})
    output.write_text(json.dumps({"files": entries, "data_note": "Raw research files are not training labels."}, indent=2), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    download_osdr()
    nlsp = discover_nlsp()
    LOGGER.info("Found %d locally downloaded NLSP export(s)", len(nlsp))
    PROCESSED.mkdir(parents=True, exist_ok=True)
    corpus = build_synthetic_corpus()
    output = PROCESSED / "synthetic_demo_70day.csv"
    corpus.to_csv(output, index=False)
    LOGGER.warning("Wrote %s (%s rows): synthetic demo data, not NASA or clinical observations", output, len(corpus))
    local_files = list(RAW_OSDR.glob("*")) + [Path(item["path"]) for item in nlsp]
    write_manifest([path for path in local_files if path.is_file()], PROCESSED / "raw_manifest.json")


if __name__ == "__main__":
    main()
