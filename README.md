# AstroGuard

AstroGuard is a research prototype with one connected demo flow:

**OSDR/NLSP collection and local demo observations → normalization → synthetic benchmark training → FastAPI forecasts and anomaly checks → dashboard.**

The checked-in astronaut measurements and the model training corpus are simulated. OSDR/NLSP files are cached and catalogued as raw research inputs; they are not silently converted into astronaut labels or used to train these models. See [data provenance](docs/DATA_PROVENANCE.md) before interpreting any output.

## Run the unified backend and dashboard on Windows

From the repository root:

```powershell
cd backend
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ml.pipeline --offline
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then open:

- Dashboard: <http://127.0.0.1:8000/dashboard>
- API docs: <http://127.0.0.1:8000/docs>
- Health/readiness: <http://127.0.0.1:8000/api/v1/health>

`--offline` skips NASA network collection and uses the repository's local simulated data. To attempt OSDR collection as part of the same pipeline, run `python -m ml.pipeline` instead. NLSP exports, if available, belong in `backend/data/raw/nlsp/`.

## Verify

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The pipeline entry point writes a normalized daily demo dataset, rebuilds the synthetic 30-astronaut/70-day training corpus, trains the five model artifacts, and records a run manifest at `backend/data/processed/unified_pipeline_manifest.json`.

## API path

- `GET /api/v1/ml/data-status` shows collected files, normalized demo data, and loaded model artifacts.
- `GET /api/v1/ml/forecast-from-dataset/{astronaut_id}?mission_day=20` sends normalized local demo measurements through the same forecast path as the JSON API.
- `POST /api/v1/ml/forecast` accepts a 14-day baseline and up to 14 days of mission telemetry.
- `GET /api/v1/ml/demo-mission` returns the standalone 30-day model demonstration.
- `GET /api/v1/ml/model-info` describes artifacts, demo thresholds, and limitations.

See [API contract](docs/API_CONTRACT.md) and [architecture](docs/ARCHITECTURE.md) for details.

## Scope and safety

This project does not provide a doctor's assessment, medical clearance, treatment instruction, or clinically validated prediction. The model risk scores, alert thresholds, and countermeasure effect estimates are synthetic demo constructs. Missing inputs are reported and may be imputed to run the demonstration. Do not enter personal health information.
