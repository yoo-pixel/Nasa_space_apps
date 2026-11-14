# NASA data dictionary

## Dataset manifest fields

Every external package added under `data/nasa/` should have a sidecar manifest recording:

| Field | Meaning |
| --- | --- |
| `source` | Repository, portal, instrument network, or study owner. |
| `source_url` | Canonical dataset page or exact API query. |
| `accession` | NASA study/experiment identifier, when available. |
| `version` | Source version/release; preserve the source's own value. |
| `retrieved_at` | Timestamp the raw artifact was downloaded. |
| `time_start_utc`, `time_end_utc_exclusive` | Coverage interval, where applicable. |
| `organism_or_platform` | Human, model organism, ISS, ground analog, or other platform. |
| `record_count` | Number of records/rows in the artifact, not participant count. |
| `units` | Explicit unit per measurement field. Do not infer missing units. |
| `access_conditions` | License, approval/request requirement, and file status from the source record. |
| `processing` | Transformation from immutable raw artifact to processed output. |
| `sha256` | Hash of the preserved raw artifact. |

## RadLab snapshot fields

| Field | Unit / interpretation |
| --- | --- |
| `timestamp_utc` | NASA API timestamp treated as UTC. |
| `instrument_id` | Detector/configuration identifier as supplied by RadLab. |
| `spacecraft` | ISS in the included sample. |
| `absorbed_dose_rate_uGy_per_hour` | Absorbed dose rate in microgray per hour (µGy/hour). |
| `dose_equivalent_rate_uSv_per_hour` | Dose-equivalent rate in microsievert per hour (µSv/hour); may be null. It is kept distinct from absorbed dose rate. |
| `latitude_degrees`, `longitude_degrees` | Detector/platform location when supplied. |
| `altitude_km` | Altitude when supplied, in kilometres. |

These are detector/environment measurements. Do not assign them to an astronaut, label them as individual dosimeter results, or combine Gy and Sv quantities into a single score.

## Data layers

- `raw/`: immutable downloaded bytes from an identified source.
- `processed/`: derived files with a recorded transformation and preserved source units.
- `validated/`: files checked against schema/range and provenance expectations; validation does not imply clinical validity.
- `metadata/`: manifests, source catalog entries, and retrieval notes.
