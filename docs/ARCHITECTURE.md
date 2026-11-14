# Architecture

## Components

- React + TypeScript single-page application served by Vite.
- Axios service modules call the REST API; React Query handles request caching and refresh.
- FastAPI exposes versioned endpoints at /api/v1.
- Pydantic validates request and response shapes.
- SQLAlchemy maps missions, users, astronauts, medical history, measurements, baselines, analysis results, alerts, and data sources.
- SQLite is the default local database; set DATABASE_URL to use PostgreSQL.
- The ML package is isolated from API and persistence code. It currently uses a robust statistical band because no labeled source dataset is present.

## Data flow

    React page → typed service → FastAPI/Pydantic → endpoint/service → SQLAlchemy → SQLite or PostgreSQL
                                                           ↓
                                                    analysis module
                                                           ↓
                                             analysis result + alert

## Configuration and operation

The database connection is selected by DATABASE_URL. FastAPI creates the schema and inserts seed records only when the astronaut table is empty. Alembic is configured for explicit migrations. CORS allows the local Vite origins.

## Trust boundaries and prototype limits

No user authentication, authorization middleware, or production secrets management is implemented. Local reviewer names are labels only. Do not connect real health data until identity, access control, audit policy, encryption, and deployment controls are designed and reviewed.
