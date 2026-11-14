# Data provenance and model scope

| Data | Location | Processing | Used by models? |
|---|---|---|---|
| Repository long-form demo observations | `data/synthetic/measurements.csv` | Reviewed variable/unit mapping to daily rows; keeps unavailable values null; provenance and quality labels retained | Used by the local forecast adapter as simulated inference input only |
| NASA OSDR study exports | `backend/data/raw/osdr/` | Downloaded/cached as raw files; file discovery and hash manifest | No; no cross-study mapper or compatible daily forecast target exists |
| Manual NLSP exports | `backend/data/raw/nlsp/` | Locally discovered and inspected for filename/columns | No; no reviewed mapper or compatible daily target exists |
| Synthetic 70-day benchmark | `backend/data/processed/synthetic_demo_70day.csv` | Deterministic generated physiology/environmental features and labels | Yes; all five artifacts are trained on this benchmark |

The long-form demo values are explicitly marked simulated. The normalizer maps only measures with a known name/unit pair. It uses resting-phase heart-rate readings, derives pulse pressure and sleep efficiency only where their inputs exist, derives baseline BMD drift from a pre-flight BMD anchor, and computes cumulative dose only while daily dose readings are present. This dataset has no in-mission DXA readings, so mission BMD drift remains missing. It does not infer cabin CO₂, gravity during the mission, WinSCAT, NLR, calcium, exercise load, or pre-medical history when the source lacks them. Historical measurements outside the daily demo window stay in the raw file and are excluded from normalized daily telemetry.

The serving adapter may impute missing feature values from the personal baseline or documented demonstration defaults. Responses report missing fields and per-system observed-input coverage. Alert checks use observed sensors only; the multivariate anomaly detector skips classification when its six required sensor inputs are incomplete.

The synthetic benchmark can demonstrate software behavior and data flow. It cannot establish physiological validity, clinical accuracy, treatment effects, or NASA compliance. The exported countermeasure effect estimate is intentionally `null` until validated outcome data and an appropriate evaluation are available.

Each unified pipeline run writes a manifest with repository-relative paths, byte sizes, and SHA-256 fingerprints for the source, normalized output, cached research files, training data, and model artifacts so a teammate can confirm which files were used.
