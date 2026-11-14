# Database schema

All primary keys are UUIDs. Timestamps are stored with timezone support. Structured findings and symptoms use JSON columns (PostgreSQL stores them as JSON-compatible values).

| Table | Purpose | Main relationships |
|---|---|---|
| missions | Mission metadata | One mission to many astronauts |
| users | Reviewer identity placeholder | Intended for review attribution; no authentication is wired |
| astronauts | Crew profile and mission status | Belongs to a mission; owns history, readings, baselines, analyses, alerts |
| medical_history | Profile history entries | Belongs to an astronaut |
| learning_sessions | Start time and reviewer for each personal learning window | Belongs to an astronaut |
| personalized_profiles | Human-approved profile created after evidence requirements are met | Belongs to an astronaut and learning session |
| bone_health_assessments | Source-linked scan, turnover, exercise, or nutrition records | Belongs to an astronaut |
| radiation_exposure_records | Dosimeter quantity, unit, source, mission phase, event, and shielding context | Belongs to an astronaut |
| measurements | Metric value, unit, time, source, symptoms | Belongs to astronaut and optionally data source |
| metric_baselines | Per-astronaut descriptive bands | Unique astronaut + metric |
| analysis_results | Model name/version, summary, findings, score | Belongs to astronaut; can generate alerts |
| alerts | Flag and human review lifecycle | Belongs to astronaut; optionally links analysis and measurement |
| data_sources | Source attribution and connection status | Can be referenced by measurements |

Indexes cover mission/status, astronaut/time, measurement metric/time, analysis chronology, learning chronology, bone/radiation chronology, and alert review status. The migration adds fields and tables without dropping existing health records.
