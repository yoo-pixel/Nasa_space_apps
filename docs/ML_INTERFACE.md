# Analysis interface

Call analyze_health(astronaut_id, measurements, baseline, medical_history) through backend/app/ml/inference.py.

The current implementation compares each metric to a personal median and a robust median-absolute-deviation band. It returns structured findings, descriptive scores, explanations, and a human-review flag. The service persists the result and creates a review alert for an outlying measurement.

This method is experimental and has no scientific validation or accuracy claim. The baseline band in the demo is computed from generated values and is not a clinical interval. No NASA dataset, trained model, or medical decision rule is bundled. A future labeled dataset should drive algorithm selection and evaluation before any trained model is considered.
