# PranaGuard — technical report

## 1. Executive summary
A working React/FastAPI/SQLite research prototype implements a persistent COPD body × environment twin for120 synthetic patients over60 days. All three risk horizons are real fitted-model outputs, not hardcoded predictions. The engineering workflow is functional; the primary72h model is poor, all primary horizons have zero sensitivity at the fixed alert cutoff, and this is not clinical validation. Public publishing and the actual video upload remain pending.

## 2. Problem and intended healthcare workflow
COPD exacerbation warning would require personalized context and changing signals. The prototype lets a clinician review a synthetic cohort, inspect baseline/current physiology, ambient context and separate24/48/72h probabilities, understand drivers, acknowledge/resolve alerts, record review actions and compare non-causal feature-path assumptions. The four Indian demonstration locations do not imply clinical collaborators or deployment.

## 3. Source specification and scope
The named DOCX was absent; the user explicitly authorized the master message as the specification. No absent document content, team identity or affiliation was invented. The mandatory stack is used. There are no container or Streamlit dependencies. Team/college and public/video URLs are explicit placeholders.

## 4. Implemented twin state and transitions
The state includes patient ID, synthetic profile, immutable version, replay hour/time, baseline, current measurements, shared causal feature vector, three probabilities, model version, missing fields, eligibility warnings and source freshness. First72h medians are fixed before prediction. Every replay step ingests the next deterministic hourly record for all120 twins, infers the horizon models and atomically persists versions, cursor and new alerts. SQLite WAL, foreign keys and rollback protect local consistency. Restart reopens saved states, not a recomputed fake trajectory. One worker is required; distributed coordination is out of scope.

## 5. Data generation, validation and provenance
Seed2026 generates172,800 rows and263 stochastic onsets. Clinical profiles, physiological streams, symptoms, steps, sleep and adherence are synthetic. A stochastic latent burden influenced by ambient exposure and adherence produces noisy signals and probabilistic onsets with a refractory period. No future event is injected directly as a feature, and no medical calibration of this process is claimed. Four wearable fields have independent missingness after warm-up. Ingestion checks ranges, required fields, duplicate hours, time alignment and calibration coverage before feature engineering.

Eight successfully retrieved public JSON caches each cover1,440 hours (air + weather at four cities). PM2.5/PM10/NO2/O3 come from Open-Meteo/CAMS global modeled ambient concentrations; temperature/humidity use the Historical Weather API. Raw responses, URLs, retrieval timestamps and SHA-256 values are versioned. These are coarse gridded products, not actual personal dose. They are historical2026-08-01 to2026-09-29 UTC, not current environmental observations. CC BY4.0 attribution is included; free hosted access is non-commercial fair use. No restricted clinical dataset is redistributed.

The generator errors on absent/short/gapped caches unless a labelled synthetic-environment option is explicitly chosen. Runtime inference/replay requires no external network. Historical/revised products are not a verified as-issued production data feed, despite causal timestamp use.

## 6. Features and labels
Static inputs: age, FEV1, prior exacerbations, pack-years and BMI. Body streams: SpO2, HR, RR, symptom score, adherence, steps, sleep, causal6h means/differences and24h adherence. Environment: current ambient/weather fields, trailing24h PM2.5 and past6h change. Personalization: patient-relative deviations, steps ratio and baseline physiology.

For eligible hour t, y_h=1 when an artificial new onset occurs in(t,t+h]. Otherwise0. Warm-up hours, active episodes/onsets and the final72h without full follow-up are excluded from all horizon experiments. This is not a clinical adjudication or a validated exacerbation endpoint.

## 7. Leakage-aware experiment design
There are72 train patients,24 disjoint calibration patients and24 further test patients at later calendar dates. A minimum72h purge separates partitions. Train/cal rows are sampled every3h; test uses every eligible hour. Actual counts: 14605 train, 1377 calibration and 4699 test windows. IDs/time/location names and future labels/event flags are excluded. Baselines use first72h only. Rolling means look backward; imputation and LR scaling fit on train only. Calibration fits on calibration only. No hyperparameter or threshold selection was performed on test.

## 8. Models, calibration and actual evaluation
Logistic Regression with standard scaling is the baseline. LightGBM uses160 trees, learning rate.045,15 leaves, depth5, minimum65 child samples, regularization3 and seed2026. Each horizon has a separate classifier and Platt logistic calibrator. Threshold.35 is a predeclared demo convention. All four LightGBM input-group ablations and the full LR baseline were executed for all three horizons.

| Model | Horizon | AUROC | AUPRC | Brier |
|---|---:|---:|---:|---:|
| LightGBM | 24h | 0.6916 | 0.0882 | 0.0279 |
| LightGBM | 48h | 0.6144 | 0.0968 | 0.0557 |
| LightGBM | 72h | 0.3951 | 0.0593 | 0.0853 |
| LogisticRegression | 24h | 0.6619 | 0.1993 | 0.0260 |
| LogisticRegression | 48h | 0.6285 | 0.1841 | 0.0537 |
| LogisticRegression | 72h | 0.6253 | 0.2281 | 0.0800 |

The72h primary AUROC0.3951 and AUPRC0.0593 are poor; prevalence is0.0773. LR performs better at72h. At threshold.35 all three primary models yield zero true positives on the held-out hours; the72h matrix is TN4336, FP0, FN363, TP0. Five test-window onsets were available and zero met the72h early-alert rule. No positive lead-time claim is supportable; median detected lead time is undefined, not zero hours.150 patient-cluster bootstrap resamples quantify some instability, not clinical confidence. Shared ambient series introduce additional dependence.

### All executed ablations
| Model / ablation | Horizon | AUROC | AUPRC | Brier |
|---|---:|---:|---:|---:|
| LogisticRegression / personalized | 24h | 0.6619 | 0.1993 | 0.0260 |
| LogisticRegression / personalized | 48h | 0.6285 | 0.1841 | 0.0537 |
| LogisticRegression / personalized | 72h | 0.6253 | 0.2281 | 0.0800 |
| LightGBM / static_only | 24h | 0.2688 | 0.0214 | 0.0292 |
| LightGBM / static_only | 48h | 0.2246 | 0.0390 | 0.0565 |
| LightGBM / static_only | 72h | 0.2197 | 0.0550 | 0.0816 |
| LightGBM / body_stream | 24h | 0.6242 | 0.0408 | 0.0294 |
| LightGBM / body_stream | 48h | 0.6160 | 0.0688 | 0.0561 |
| LightGBM / body_stream | 72h | 0.6358 | 0.1086 | 0.0815 |
| LightGBM / full_environment | 24h | 0.6991 | 0.0676 | 0.0282 |
| LightGBM / full_environment | 48h | 0.6613 | 0.0939 | 0.0558 |
| LightGBM / full_environment | 72h | 0.3119 | 0.0514 | 0.0816 |
| LightGBM / personalized | 24h | 0.6916 | 0.0882 | 0.0279 |
| LightGBM / personalized | 48h | 0.6144 | 0.0968 | 0.0557 |
| LightGBM / personalized | 72h | 0.3951 | 0.0593 | 0.0853 |

No consistent performance improvement is established. Full-environment72h is worse than body-stream alone; personalization does not establish clinical benefit. The72h Platt slope is negative, reversing raw tree-score direction. The result was retained rather than silently post-hoc corrected on the test set. This is an explicit model stability/safety concern requiring a new pre-registered development/validation effort. ROC, PR, calibration arrays, confusion matrices, CI estimates and prediction-level outputs are included in artifacts.

## 9. Explainability
Native LightGBM pred_contrib provides exact additive TreeSHAP values in raw tree log-odds. Base plus contributions equals the raw score, checked numerically. Final calibrated probabilities are reported separately. Contribution changes compare two persisted feature vectors. Patient-relative deviations are differences from fixed first72h baselines. A positive raw contribution is not necessarily a calibrated risk increase when calibration slope is negative. Associations cannot establish clinical causes. The non-tree fallback is documented as one-feature reference perturbation, not additive SHAP.

## 10. Scenario methodology and integrity
Observed history is copied only up to the current saved hour. A baseline branch persists current physiology/exposure/adherence/activity; a scenario branch changes PM2.5 with a6h exponential transition, scales PM10, sets adherence and multiplies steps. All causal features are recalculated over72 projected hours; the same actual models infer each projected-time horizon. The chart is not a cumulative-risk curve: a72h model at projected+72h extends beyond the original horizon. No future realized data, causal treatment response or assumed physiological recovery is used. Results persist separately with original state version and assumptions. Tests compare the original saved state byte-for-byte and perturb future raw rows to establish branch isolation.

## 11. Application and APIs
Seven working React sections cover cohort/search/pagination, patient baseline/history/version ledger, explainability, scenario calculations/saved runs, actual model validation, persisted alerts/actions, and system/data provenance. Charts receive API data. Empty/null history is shown honestly. Export produces a real JSON twin snapshot. Replay controls call backend mutation endpoints. WebSockets invalidate views after twin/alert changes; REST polling is a fallback. Vite uses relative same-origin API paths and accepts the hosted preview. FastAPI OpenAPI documents all routes.

## 12. Testing and reproducibility
Executed backend tests cover inference consistency, causal features/splits, calibration warm-up, scenarios, real model alerts, intervention persistence, replay bounds/determinism, authorization, WebSockets, SQLite rollback, ingestion checks, source status and recomputed metrics. React Testing Library covers actual captured API fixtures, search/filter/pagination, versions, horizon controls, scenario POSTs, notes, status/tokens and error handling. Chromium tests exercise the real servers, all main views, source data, original-state preservation, timed replay, actual false-positive alert lifecycle, reload persistence, export and mobile layout while external browser HTTP is blocked. Final actual results:41 backend tests,14 frontend tests and18 Chromium integration checks pass; clean-clone/new-venv/npm-ci setup and the production frontend build also pass. Exact results are in verification logs/reports. Reproduction executes the generator/training again and compares dataset bytes plus all primary predictions/metrics.

## 13. Safety, security and limitations
All patient labels are visibly synthetic. This is not a medical device, diagnosis, triage service or treatment recommendation. No hospitalization reduction, validated lead time or clinical benefit is proven. The synthetic generator, small event count, poor72h performance, negative calibration slope, zero threshold sensitivity, correlated windows, coarse shared ambient context, missingness assumptions and retrospective data products limit conclusions. Default auth is off for local synthetic review; optional shared token gates writes but is not RBAC. No real data should be entered. Production would require TLS, identity/consent, regulated audit retention, rate limits, secure storage, verified device ingestion and clinical governance. Joblib loads trusted local bundles only.

## 14. Demonstration and delivery status
The replay example PG-0071 is chosen retrospectively for its maximum actual72h score across the synthetic cohort. Reset at hour1039 and+12h reaches hour1051, score0.3551213865 and synthetic label0, a false positive. It is not a held-out detection success. The20-minute recording package calls this out explicitly. Team/institution details, authorized public repository publication, actual Unlisted YouTube recording/upload and signed-out public-access checks remain mandatory human work. A generated file or preview alone does not prove submission readiness.

## 15. Reproduction and references
Use exact commands in the root README. Dataset SHA-256: `a9fddac47dfd28548feb336564928b7510b13d35d89a845727b12a54b3e54a5d`. See source cache manifest, split manifest, model card, data provenance, licenses, API reference, architecture exports and submission checklist. Public source documentation: https://open-meteo.com/en/docs/air-quality-api ; https://open-meteo.com/en/docs/historical-weather-api ; https://open-meteo.com/en/licence . Challenge reference: https://unstop.com/hackathons/crp-digital-twin-challenge-2026-happiest-health-1757873 . No independent clinical validation publication is claimed.
