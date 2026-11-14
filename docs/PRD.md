# Product requirements

## Purpose

AstroGuard is a research prototype for organizing astronaut health profiles, measurements, personalized descriptive baselines, and review prompts.

## Users

- Mission medical personnel reviewing crew data
- Researchers inspecting longitudinal demonstration measurements
- Developers integrating an approved data source

## Core flows

1. Review mission-level counts, trends, and open flags on the dashboard.
2. Search the crew roster and open a profile.
3. Enter one or more physiological observations in a check-in.
4. Compare observations against the astronaut's available descriptive personal history.
5. Inspect the alert explanation and source reading.
6. Record reviewer notes and acknowledge, resolve, or reopen the alert.
7. Inspect data provenance and source readiness.

## Safety and provenance requirements

- Synthetic values are labeled in the user interface and database.
- NASA OSDR is shown only as an unconnected integration target; no NASA observations are fabricated.
- Analysis flags are not diagnoses and do not make decisions.
- The current prototype has no authentication and is unsuitable for real health records.
