# NASA research and data workspace

## Folders

- `challenge_resources/` — exact challenge-provided resources after the selected challenge page is identified.
- `standard_measures/` — approved Spaceflight Standard Measures exports and metadata.
- `bedrest_studies/` — selected NLSP analog study exports, keeping each campaign identifiable.
- `inspiration4/` — selected OSDR study files, separated by accession and assay.
- `twins_study/` — public study documents and datasets with source metadata.
- `radiation/raw/`, `processed/`, `validated/` — RadLab snapshots and derived tables.
- `environment/raw/`, `processed/`, `validated/` — EDA telemetry when an exact mission/export is selected.
- `metadata/` — manifests, retrieval notes, exact API queries, checksums, and license/access notes.

Only `radiation/` currently contains data. Raw API JSON remains unchanged; its UTC CSV is a derived convenience view. OSDR and NLSP records in the AstroGuard UI are a catalog, not imported observation files.

See `../../docs/NASA_DATA_CATALOG.md` for the source map and `../../docs/DATA_DICTIONARY.md` for required fields and units.
