"""Run the unified collection, normalization, dataset-preparation, and ML flow.

Usage from ``backend``::

    python -m ml.pipeline --offline
    python -m ml.pipeline

OSDR/NLSP files are collected and catalogued as research inputs. Until a
study-specific mapper and compatible outcome labels exist, training remains on
the separately provenance-marked synthetic benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml.data_loader import PROCESSED, RAW_NLSP, RAW_OSDR, build_synthetic_corpus, discover_nlsp, download_osdr
from ml.research_data import NORMALIZED_OUTPUT, SOURCE_MEASUREMENTS, normalize_measurements
from ml.train_ml import DATA_PATH, MODEL_DIR, train_all

MANIFEST_PATH = PROCESSED / "unified_pipeline_manifest.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        relative_path = path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        relative_path = path.name
    return {"path": relative_path, "size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def run_pipeline(*, offline: bool = False) -> dict[str, Any]:
    """Collect sources, normalize the checked-in demo stream, and train models."""
    collection_status = [] if offline else download_osdr(timeout=15)
    nlsp_files = discover_nlsp()

    normalized = normalize_measurements()
    NORMALIZED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(NORMALIZED_OUTPUT, index=False)

    training_data = build_synthetic_corpus()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    training_data.to_csv(DATA_PATH, index=False)
    artifacts = train_all(training_data)
    metrics_path = MODEL_DIR / "training_metrics.pkl"
    metrics: dict[str, Any] = {}
    if metrics_path.exists():
        import joblib

        metrics = joblib.load(metrics_path).get("metrics", {})

    osdr_files = sorted((path for path in RAW_OSDR.glob("*") if path.is_file()), key=lambda path: path.name)
    nlsp_paths = sorted((Path(item["path"]) for item in nlsp_files), key=lambda path: path.name)
    artifact_paths = sorted(artifacts.values(), key=lambda path: path.name)

    summary = {
        "pipeline_id": "astroguard-unified-demo-v1",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "offline": offline,
        "collection": {
            "osdr": collection_status,
            "nlsp_local_file_count": len(nlsp_files),
            "osdr_files": [_fingerprint(path) for path in osdr_files],
            "nlsp_local_files": [_fingerprint(path) for path in nlsp_paths],
        },
        "processing": {
            "source": _fingerprint(SOURCE_MEASUREMENTS),
            "data_origin": "synthetic_demo_only",
            "normalized_output": _fingerprint(NORMALIZED_OUTPUT),
            "normalized_rows": int(len(normalized)),
            "normalized_astronauts": int(normalized["astronaut_id"].nunique()),
        },
        "training": {
            "source": _fingerprint(DATA_PATH),
            "data_origin": "synthetic_demo_only",
            "rows": int(len(training_data)),
            "astronauts": int(training_data["astronaut_id"].nunique()),
            "metrics": metrics,
            "artifacts": [_fingerprint(path) for path in artifact_paths],
            "note": "OSDR/NLSP files are not training labels; their study-specific schemas need reviewed mappers first.",
        },
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="skip OSDR network collection and use local/cached inputs")
    args = parser.parse_args()
    result = run_pipeline(offline=args.offline)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
