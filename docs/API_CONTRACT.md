# API contract

Base URL: `http://127.0.0.1:8000/api/v1`. The static dashboard is served at `/dashboard`.

Every ML response includes `clinical_use: false`, the model data origin, and a limitation note. Demo risk scores and thresholds are not medical probabilities or NASA limits. Missing inputs are listed in `data_quality`; feature imputation does not make them observed.

## System status and model metadata

- `GET /health` — service liveness plus forecast readiness (`ready`, `degraded`, or `unavailable`) and per-artifact load status.
- `GET /ml/model-info` — model names, feature names, demo threshold metadata, data origin, limitations, and the narrow synthetic grouped-CV metric (heart rate at `t+1` only).
- `GET /ml/data-status` — raw OSDR/NLSP cache file names, normalized demo dataset coverage, and training/model availability. It reports status; it does not start downloads.

## Forecasts

- `POST /ml/forecast` — accepts `astronaut_id`, exactly 14 `earth_baseline` observations, 1–14 `mission_telemetry` observations, optional `mission_day`, and optional `pre_medical`. Each observation may contain the supported vital, lab, radiation, gravity, and cabin fields. Unknown fields are rejected. Unavailable measures may be `null`.
- `GET /ml/forecast-from-dataset/{astronaut_id}?mission_day=20` — builds the same request shape from normalized local synthetic measurements and calls the shared forecast service.
- `GET /ml/demo-mission` — returns the independent 30-day example timeline with synthetic CO₂ and exercise events.

Forecast output contains the four system trajectories, demo alert flags, observed-input coverage, and a human-review-only action label. `projected_risk_reduction_pct` and `scenario_candidate_for_review` are retained for response compatibility but return `null`; this prototype has no validated countermeasure effect estimate.

Telemetry fields also have broad physical sanity bounds and reject inconsistent systolic/diastolic ordering. These bounds catch malformed units/values; they are not medical thresholds.

## Error behavior

- `404` — requested astronaut is absent from the local demo dataset.
- `422` — invalid request shape, unavailable mission day, or insufficient consecutive daily rows.
- `503` — required model artifacts or local demo data are unavailable.

All endpoints are demonstration interfaces. They are not a substitute for qualified medical review or mission procedures.
