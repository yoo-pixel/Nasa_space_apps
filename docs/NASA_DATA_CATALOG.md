# AstroGuard NASA research catalog

This catalog turns the NASA sources identified for AstroGuard into a navigable inventory. It distinguishes research guidance, human/analog studies, dataset records, and tools. Except for the one-hour RadLab snapshot described below, cataloged items are references only: their research files have not been downloaded or mapped into astronaut health records.

## NASA framework

NASA's Human Research Program groups spaceflight hazards as space radiation, isolation and confinement, distance from Earth, gravity fields, and hostile/closed environments. NASA describes interactions between hazards and documents associated physiology, behavioral-performance, operational, and radiation risks. See the [hazards overview](https://www.nasa.gov/hrp/hazards/), [risks overview](https://www.nasa.gov/hrp/risks/), and [Human System Risk Board](https://www.nasa.gov/directorates/esdmd/hhp/human-system-risk-board/).

AstroGuard maps these areas to monitored domains as a research organization aid. A NASA hazard or risk reference does not validate an individual medical alert or diagnosis.

## Repositories and human/analog studies

| Source | What is identified | AstroGuard relevance | Current project status |
| --- | --- | --- | --- |
| [NASA Life Sciences Portal (NLSP)](https://nlsp.nasa.gov/) / Life Sciences Data Archive | Search and access path for NASA life-sciences research, including human and analog work. Some records or files require a data request or approval. | Find studies, measurement definitions, and data request routes. | Cataloged; no bulk NLSP download. |
| [Spaceflight Standard Measures](https://ntrs.nasa.gov/citations/20230014025) | Core measures across preflight, in-flight, and postflight windows. NASA's presentation reports actigraphy in two-week windows; other measures have different schedules. The presentation summarizes data collected from 31 ISS crew members. | Rationale for an activity/sleep observation window; not evidence that every physiological variable is continuous or daily. | Reference only; no individual-level NASA data imported. |
| [UTMB Bedrest Campaign 1](https://nlsp.nasa.gov/) | Ground analog campaign identified in the NASA portal. | Inspect source-record variables and cohort before any analysis. | Cataloged; record-level file inventory pending. |
| [UTMB Bedrest Campaign 3](https://nlsp.nasa.gov/) | Ground analog campaign identified in the NASA portal. | Candidate bone, cardiovascular, and sensorimotor research. | Cataloged; record-level file inventory pending. |
| [UTMB Bedrest Campaign 11](https://nlsp.nasa.gov/) | NASA NLSP describes 70 days of six-degree head-down bed rest with countermeasure and functional-task research. This is a ground analog, not an astronaut flight cohort. | Explore exercise/performance and longitudinal analog measures. | Cataloged; no files imported. |
| [NASA Twins Study background](https://www.nasa.gov/humans-in-space/the-human-body-in-space/) | Published comparison of one long-duration spaceflight participant and one terrestrial twin across several research areas. | Scientific context and hypothesis generation. | Reference only; not treated as a broad model-training cohort. |

## Inspiration4 OSDR study records

These are distinct biospecimen/assay study records related to the short Inspiration4 mission, not continuous health-monitoring channels. A study page's live files panel is the authority for file availability, licensing, and version. The app links to each record and does not assume data access from its identifier alone.

| OSDR accession | Study material / topic noted for investigation | AstroGuard use | Status |
| --- | --- | --- | --- |
| [OSD-569](https://osdr.nasa.gov/bio/repo/data/studies/OSD-569) | Whole blood | Blood and cellular research context | Cataloged; not imported |
| [OSD-570](https://osdr.nasa.gov/bio/repo/data/studies/OSD-570) | Peripheral blood mononuclear cells (PBMC) | Immune/cellular research context | Cataloged; not imported |
| [OSD-571](https://osdr.nasa.gov/bio/repo/data/studies/OSD-571) | Plasma | Biomarker research context | Cataloged; not imported |
| [OSD-572](https://osdr.nasa.gov/bio/repo/data/studies/OSD-572) | Skin, oral, and nasal swabs | Microbiome research context | Cataloged; not imported |
| [OSD-573](https://osdr.nasa.gov/bio/repo/data/studies/OSD-573) | Dragon capsule samples | Spacecraft/environmental microbiology context | Cataloged; not imported |
| [OSD-574](https://osdr.nasa.gov/bio/repo/data/studies/OSD-574) | Skin biopsy | Biological response research context | Cataloged; not imported |
| [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) | Serum / metabolic and immune-cardiac assays | Biomarker research context | Cataloged; not imported |
| [OSD-630](https://osdr.nasa.gov/bio/repo/data/studies/OSD-630) | Stool | Gut microbiome research context | Cataloged; not imported |
| [OSD-656](https://osdr.nasa.gov/bio/repo/data/studies/OSD-656) | Urine | Biomarker research context | Cataloged; not imported |
| [OSD-687](https://osdr.nasa.gov/bio/repo/data/studies/OSD-687) | T-cell histone-modification assays | Molecular research context | Cataloged; not imported |

The [OSDR repository](https://osdr.nasa.gov/bio/repo/) and [Biological Data API documentation](https://visualization.osdr.nasa.gov/biodata/api/) are included for metadata/file discovery. OSDR contains a mix of human and model-organism work; check organism, assay, timepoint, file availability, and license on every selected record. OSDR notes that some data access can be restricted or temporarily unavailable.

## Radiation and environment sources

| Source | Data identified | Important boundary | Current project status |
| --- | --- | --- | --- |
| [RadLab portal](https://visualization.osdr.nasa.gov/radlab/) and [RadLab API](https://visualization.osdr.nasa.gov/radlab/gui/data-api/) | Instrument radiation telemetry. The API documents absorbed dose rate in µGy/hour and dose-equivalent rate in µSv/hour, with time and optional location/instrument fields. | Detector telemetry is environmental data, not a specific astronaut's personal dosimeter record. | API explorer connected in Radiation Monitoring; one-hour raw reference response and a normalized CSV are included. |
| [Environmental Data Application (EDA)](https://visualization.osdr.nasa.gov/) | NASA OSDR tool to explore ISS/ground-platform telemetry including temperature, relative humidity, CO₂, and radiation variables. | Contextual environmental readings require matching mission/platform and time; they do not establish a diagnosis. | Portal cataloged; no EDA files imported. |

## Challenge resources

The exact resources shown in AstroGuard's selected 2026 NASA Space Apps challenge have not been provided in the project. This catalog does not claim that any item here satisfies a challenge-specific eligibility rule. Add the selected challenge page/Resources list before treating that requirement as verified.

## Files in this project

- `data/nasa/radiation/raw/radlab_iss_dostel1_2023-01-01_0000-0100Z.json` — API response preserved as downloaded; ISS, DosTel1, one UTC hour, 34 rows.
- `data/nasa/radiation/processed/radlab_iss_dostel1_2023-01-01_0000-0100Z.csv` — derived table with UTC timestamps and explicit unit-bearing column names.
- `data/nasa/metadata/radlab_iss_dostel1_2023-01-01_0000-0100Z.json` — exact query, retrieval timestamp, source, units, row count, and SHA-256 of raw file.

Do not merge this environmental sample into the synthetic astronaut vitals or personal dosimeter records.
