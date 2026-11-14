# NASA research data and AstroGuard learning methodology

## Use source evidence at the right level

- NASA hazard/risk pages and research papers inform domain definitions and hypotheses. They are not measurement rows.
- Spaceflight Standard Measures supports a two-week activity/sleep observation concept for actigraphy. It does not establish that every measure is continuous for two weeks or validate AstroGuard's exact learning algorithm.
- Bed-rest studies are ground analog cohorts. Keep their platform and study conditions visible; do not relabel them as in-flight astronaut measurements.
- Inspiration4 and the Twins Study provide small, study-specific biospecimen/omics observations. They are not sufficient by themselves to train and validate general-purpose individual-health prediction models.
- RadLab and EDA are environmental/vehicle context. Do not use detector readings as an astronaut's personal dose without an independently matched personal dosimeter record.

## Minimum rules before modeling

1. Inspect the source dataset version, license/terms, access state, organisms/participants, assay, columns, units, and collection schedule.
2. Preserve raw files and checksums; create separate processed outputs and document every conversion, filter, exclusion, and join.
3. Keep participant, specimen, mission, platform, and instrument identifiers distinct. Do not join on time alone where a source-specific key is available.
4. Distinguish flight, ground analog, model organism, environmental telemetry, synthetic demonstration data, and user-entered records in storage and UI.
5. Do not merge sparse lab assays into continuous vital streams as if they were daily readings. Preserve null values and variable sampling cadence.
6. Evaluate population/site/mission leakage and validate against held-out people and studies before reporting predictive performance.
7. Treat alerts and risk estimates as research decision support requiring human review, never as autonomous diagnosis.

## Current project limits

The live app still uses clearly labeled synthetic crew vitals for its health dashboard. The project includes one small, real RadLab ISS detector export for environmental visualization only. OSDR study files, NLSP human records, EDA exports, and challenge-specific resources are cataloged but not imported. No NASA dataset is used to train the app's health model.

## Current analysis behavior

- The analysis computes descriptive personal-band comparisons from the stored baseline. Its capped band-distance score is not a probability, clinical severity score, or medical threshold.
- Each finding carries its baseline method and sample count, measurement timestamp and source type, plus up to 14 days of retrospective same-metric context from records supplied to the analysis.
- The context aggregates values by UTC date before calculating a descriptive slope. A slope is included only when at least three distinct observation dates exist. It describes observed history and is never projected into future days.
- The analysis does not read medical-history narrative, diagnose, estimate treatment, provide medical clearance, or forecast health. An out-of-band result is a prompt for qualified medical review; an in-band result does not establish that the astronaut is medically clear.
- The active baselines and live health stream are synthetic demonstration data. Clinically meaningful performance has not been evaluated. No LightGBM, Isolation Forest, SHAP, or other trained model is loaded.

NASA-STD-3001 Volume 1 requirement 7001 calls for crew health monitoring results to remain retrievable for evaluation, including trend analysis. AstroGuard's retrospective context is a research-prototype aid toward that record-review use; it does not establish NASA compliance or replace program-specific medical operations and current clinical practice.
