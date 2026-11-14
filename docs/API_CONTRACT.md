# API contract

Base path: /api/v1; JSON unless stated otherwise. UUIDs are string-encoded.

## Health and overview

- GET /health → { status, service, database }
- GET /dashboard/summary → crew/measurement/alert counts, mission name and start date, recent readings, recent alerts
- GET /dashboard/monitoring-summary → current learning, review, bone, radiation, and profile counts

## Missions and sources

- GET /missions
- POST /missions — name, optional destination, status, start_date, end_date, description
- GET /data-sources

## Astronauts

- GET /astronauts?q=&status=&mission_id=
- POST /astronauts — mission_id, full_name, callsign; optional role, nationality, status, notes
- GET /astronauts/{id}
- PATCH /astronauts/{id}

## Medical history

- GET|POST /astronauts/{id}/medical-history
- PATCH|DELETE /medical-history/{id}

History entries carry a source and verification state (`unverified`, `verified`, `not_verified`). A reviewer change records who reviewed it and when. Learning cannot start while an entry remains unreviewed.

## Measurements and baseline

- GET /astronauts/{id}/measurements?metric=&limit=
- POST /astronauts/{id}/measurements — metric, numeric value, unit; optional measured_at, source_type, symptoms, notes
- GET /astronauts/{id}/baseline

Manual check-in values use source_type: "manual"; seeded values use source_type: "simulated". The API does not accept a NASA source label because no dataset import is connected.

## Personalized learning and domains

- GET /astronauts/{id}/learning → latest 14-day session, phase, dated-reading coverage, and evidence requirements
- POST /astronauts/{id}/learning — `started_by`; starts a session after history review
- POST /learning/{session_id}/approve — `approved_by`; requires 14 elapsed days, readings on 10 distinct days, 30 readings, and 2 metrics
- GET /astronauts/{id}/health-domains → per-domain status (`data_available`, `insufficient`, `unavailable`, `not_monitored`, `awaiting_medical_review`)

Learning uses only measurements after the session start and before the current time. Safety alerts remain active. The workflow does not mark a profile ready based only on elapsed time, and approval calculates descriptive personal bands from observed readings; it does not retrain a model.

## Bone health

- GET|POST /astronauts/{id}/bone-health
- POST fields: `assessment_type` (`scan`, `turnover_marker`, `exercise`, `nutrition`), `metric`, `value`, `unit`, `source`; optional recorded_at, source_verified, notes

Values are stored as reported with units and source. There are no estimates from routine vitals or population averages.

## Radiation exposure

- GET|POST /astronauts/{id}/radiation?exposure_type=
- POST fields: `dosimeter_id`, `exposure_type` (`absorbed`, `equivalent`, `effective`, `dose_rate`), `measurement_basis` (`interval`, `cumulative`, or `rate`), `value`, `unit`, `source`; optional measured_at, mission_phase, event, shielding, source_verified, notes

Absorbed dose accepts Gy-family units; equivalent/effective dose accepts Sv-family units; dose rate accepts per-hour variants. Dose records must be marked interval or cumulative; dose-rate records use the rate basis. Values with different quantities or units are not added together and no threshold or cancer probability is derived.

## NASA environmental research feed

- GET /research/radlab?start={ISO-8601-UTC}&end={ISO-8601-UTC}&instrument={DosTel1|REM-Lid|Lidal}

The route proxies the public NASA OSDR RadLab API for ISS instrument telemetry only. The maximum requested window is 24 hours. It returns source URL, retrieval time, explicit units, and detector rows; those rows are not written to the astronaut database and are not personal dosimeter records.

## Analysis

- POST /astronauts/{id}/analysis — analyzes recent stored measurements, persists findings, and creates review alerts when values exceed the personal demo band
- GET /astronauts/{id}/analysis
- GET /astronauts/{id}/analysis/latest

## Alerts

- GET /alerts?status=&priority=
- GET /astronauts/{id}/alerts
- GET /alerts/{id}
- PATCH /alerts/{id} — optional status (open, acknowledged, resolved), reviewer_notes, reviewed_by

A status update changes the persisted alert and stamps its review time. It does not make a medical decision.
