# AstroGuard

AstroGuard is a full-stack astronaut health monitoring research prototype. It provides a crew dashboard, profiles, measurement entry, longitudinal charts, anomaly flags, a medical review workflow, and long-duration health record modules.

**Health records visible in AstroGuard are synthetic demonstration data.** One one-hour NASA OSDR RadLab ISS detector snapshot is stored under `data/nasa/radiation/`, and the Radiation Monitoring page can request RadLab data dynamically. Environmental telemetry is kept separate from astronaut health records. No NASA dataset is used to train the health model. The analysis is an experimental personal-baseline comparison; it is not a validated predictive model or a diagnostic system. Flags only request human review.

## Project layout

- frontend/ — React, TypeScript, Vite, Tailwind CSS, React Router, Recharts
- backend/ — FastAPI, Pydantic, SQLAlchemy, Alembic, statistical analysis module
- data/ — synthetic demo seeds, NASA RadLab snapshot, and source manifests
- docs/ — product, architecture, NASA catalog, data dictionary, and methodology references

## Run locally (Windows PowerShell)

### Backend

    cd "$HOME\Downloads\AstroGuard\backend"
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    uvicorn app.main:app --reload

The backend creates a local SQLite database and seeds synthetic demo records the first time it starts. The API is available at http://localhost:8000, with Swagger at http://localhost:8000/docs.

### Frontend

Open a second PowerShell window:

    cd "$HOME\Downloads\AstroGuard\frontend"
    npm install
    Copy-Item .env.example .env
    npm run dev

Open http://localhost:5173.

## PostgreSQL

For a shared development setup, create a PostgreSQL database, copy the root .env.example to .env, and set DATABASE_URL to a SQLAlchemy URL such as:

    postgresql+psycopg://astroguard:your-password@localhost:5432/astroguard

Then activate the backend virtual environment and run:

    cd "$HOME\Downloads\AstroGuard\backend"
    alembic upgrade head
    uvicorn app.main:app --reload

The connection string is read from the process environment. For example, export it in PowerShell before starting the backend:

    $env:DATABASE_URL = "postgresql+psycopg://astroguard:your-password@localhost:5432/astroguard"

SQLite is the zero-setup local default. PostgreSQL is supported through SQLAlchemy and the psycopg driver.

## Main features

- Dashboard with mission metrics, crew status, daily health trends, recent readings, and review queue
- Searchable crew roster and individual astronaut profiles
- Manual check-in form for heart rate, oxygen saturation, temperature, and blood pressure values
- Health analytics with an astronaut-specific personal demo band
- Alerts with acknowledge and resolve actions
- Medical review notes persisted by the API
- Verified medical-history workflow before a 14-day personal learning session
- Learning progress based on actual dated readings and transparent evidence requirements
- Reviewer-approved personal baselines after sufficient data collection
- Source-tracked bone-health and radiation exposure records with domain coverage states
- Searchable NASA catalog covering hazards, human studies, Inspiration4 study records, repositories, and APIs
- RadLab ISS environmental telemetry explorer with source units, timestamps, and provenance
- OpenAPI / Swagger API documentation

## Data and analysis notes

The seed script generates five fictional crew profiles, 18 days of synthetic readings, personal descriptive baselines, and a few deliberate outliers for the review flow. It writes values to the configured database and does not represent actual astronaut data.

The analysis compares a new or recent value with a median and robust spread calculated from the astronaut's synthetic history. It does not use a trained model because no suitable labeled mission dataset is included. No accuracy, clinical validation, or medical decision is claimed. The code is isolated in backend/app/ml/ so a future dataset-specific pipeline can replace it.

The included NASA Open Science Data Repository (OSDR) database row is marked **not connected** for general study import. RadLab is connected separately as a read-only environmental telemetry feed. Other NASA study entries are references only until their exact files, access terms, version, variables, and units have been reviewed.

## Prototype limitations

- There is no authentication or role-based access control. Do not use this prototype with real patient or astronaut health data.
- Review actions record a local reviewer label; they do not verify identity.
- The dashboard is for research and demonstration, not clinical use.
- Synthetic baseline bands are illustrative and should not be treated as medical reference intervals.
- The 14-day workflow is a transparent prototype rule, not a validated learning or clinical protocol. It requires 14 full elapsed days, readings on 10 separate days, 30 readings, and at least 2 metrics; a reviewer must approve the profile.
- Bone-health and radiation modules store reported observations. They do not estimate bone loss, combine radiation quantities, apply thresholds, or calculate risk probabilities.
- Vision/neuro, immune, sleep/behavioral, nutrition/renal, and dedicated exercise capture are shown as not monitored until source workflows exist.

## API overview

Base path: /api/v1

- GET /health, GET /dashboard/summary
- GET /dashboard/monitoring-summary
- GET|POST /missions
- GET /data-sources
- GET|POST /astronauts, GET|PATCH /astronauts/{id}
- GET|POST /astronauts/{id}/medical-history; PATCH|DELETE /medical-history/{id}
- GET|POST /astronauts/{id}/learning; POST /learning/{session_id}/approve
- GET|POST /astronauts/{id}/bone-health
- GET|POST /astronauts/{id}/radiation
- GET /astronauts/{id}/health-domains
- GET|POST /astronauts/{id}/measurements; GET /astronauts/{id}/baseline
- POST /astronauts/{id}/analysis; GET /astronauts/{id}/analysis[/latest]
- GET /alerts, GET /astronauts/{id}/alerts, GET|PATCH /alerts/{id}
- GET /research/radlab?start={UTC}&end={UTC}&instrument={DosTel1|REM-Lid|Lidal} (maximum 24 hours)

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md), [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md), [docs/NASA_DATA_CATALOG.md](docs/NASA_DATA_CATALOG.md), [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md), and [docs/ML_METHODOLOGY.md](docs/ML_METHODOLOGY.md) for API, schema, source, and research-reference details.

## Development

Backend dependencies are listed in backend/requirements.txt; frontend dependencies are in frontend/package.json. Alembic is configured under backend/alembic/. The API creates tables on startup for a convenient SQLite demo. Run `alembic upgrade head` after updating an existing database so new history columns are added safely.

## Tests and build

Backend tests (from the backend directory):

    python -m pip install -r requirements-dev.txt
    python -m pytest

Frontend tests and production build (from the frontend directory):

    npm install
    npm test
    npm run build
