# Data sources and provenance

## AstroGuard demonstration records

- Name: AstroGuard synthetic demonstration set
- Version: demo-1.0
- Data: fictional profiles and generated physiological readings
- Status: loaded
- Not NASA research data

## NASA sources

- NASA OSDR study pages, NLSP/LSDA, Spaceflight Standard Measures, Twins Study, UTMB campaigns, and EDA are cataloged references. Their study records/files have not been imported into the app's astronaut health database.
- A one-hour ISS DosTel1 radiation-telemetry response from NASA OSDR RadLab has been downloaded to `data/nasa/radiation/raw/`. A normalized UTC CSV is in `data/nasa/radiation/processed/` and the matching manifest is in `data/nasa/metadata/`.
- AstroGuard has a read-only backend route that requests selected ISS RadLab telemetry on demand. Those values remain environmental detector data and do not populate astronaut dose records.
- The existing NASA OSDR database source row still represents broad OSDR study ingestion and remains `not_connected`; the separate RadLab API explorer is active.

For each additional import, record the source citation, dataset version, retrieval date, license/terms, measured variables, units, organism/platform, measurement frequency, and preprocessing. Preserve the original response under `raw/`; write derived data only under `processed/`. Do not imply a variable is available unless the source export contains it.

See [NASA_DATA_CATALOG.md](NASA_DATA_CATALOG.md), [DATA_DICTIONARY.md](DATA_DICTIONARY.md), and [ML_METHODOLOGY.md](ML_METHODOLOGY.md).
