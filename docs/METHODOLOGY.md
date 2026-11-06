# Methodology — implemented, not a proposed experiment

## Data and target
120 synthetic patients over60 days are generated with seed2026; cached public ambient model data are joined by location/hour. No real clinical participants, measured personal exposure or validated disease generator is involved. An eligible hour predicts a new stochastic onset in `(t,t+h]` for h=24,48,72. Active episodes/onsets, first72h warm-up and final72h with incomplete follow-up are excluded.

## Causal features and personalization
A shared feature module serves training, replay and branching. Personal baselines are medians of the first72 observed hours and precede all fitted/evaluated states. Current values, trailing6h/24h windows and past6h changes are inputs; no centered window/backfill/future signal is used. Patient ID, city labels, timestamp, hour index, event flags and future labels are excluded. Median imputers and LR scaling fit on train only.

## Frozen split and fitting
72 train patients,24 disjoint calibration patients,24 further test patients; calendar feature windows are also separated by ≥72h. Train/calibration rows are sampled every3h; test retains all eligible hourly windows. Actual sampled counts are14,605 train,1,377 calibration and4,699 test. Exact IDs and calendar/hour bounds are in `artifacts/split_manifest.json`.

Three LR baselines and12 LightGBM experiments are executed: static-only, body-stream, full environment and personalized inputs for each horizon. Fixed LightGBM configuration:160 trees,.045 learning rate,15 leaves, max depth5, minimum65 child samples, regularization3, deterministic seed2026. A separate logistic Platt calibration is fitted to each model's disjoint calibration predictions. No test-dependent hyperparameter or threshold selection is performed.

## Metrics and uncertainty
AUROC, AUPRC, Brier, log loss, precision/recall/specificity, confusion matrices, ROC/PR/calibration arrays and patient-cluster bootstrap intervals are executed, not typed into the dashboard. Threshold.35 is a predeclared demonstration convention. Hourly windows overlap and are correlated; shared city exposure adds further dependence. Only5 test-window onsets are present. Lead-time audit uses the earliest eligible72h score≥.35 in the prior72h; undetected events are not assigned artificial lead times. In this run none of5 is detected, so median detected lead time is undefined.

## Negative results and calibration audit
The72h primary model AUROC is0.3951 and AUPRC0.0593, below prevalence0.0773. LR is stronger at72h. No consistent ablation improvement is established. All primary horizons have zero sensitivity at.35. The72h fitted Platt slope is negative, reversing raw-score direction; it is retained and disclosed rather than silently post-hoc corrected using test outcomes. This instability requires new development/validation data and blocks clinical interpretation.

## Explainability and scenarios
Native TreeSHAP is additive in raw tree log-odds only, not final calibrated probability or causal effect. Driver deltas compare saved versions. Scenario branches copy only observed past and project assumptions; physiology persists at current observations, PM2.5 transitions over6h, PM10 scales proportionally, adherence/steps change as specified. Shared causal features are recomputed and actual model inference runs at projected times. Results persist separately without overwriting the original state. No future realized records, causal response or treatment efficacy is assumed.

## Auditability
All15 experiments were reproduced with identical dataset bytes, primary predictions and reported metrics. Main metrics were independently recomputed from saved test predictions. Full actual outputs, split metadata, calibration audit and hashes are in `artifacts/`; test/reproduction evidence is in `docs/verification/`. See the technical report and model card for limitations, provenance and detailed results. No clinical validation is implied by software reproducibility.
