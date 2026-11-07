# Model card — pg-synthetic-v1

## Intended use and prohibited use
Software research with explicitly synthetic COPD twins. Not diagnosis, triage, treatment, or clinical decision support. No clinical validation, real patient data or prospective benefit evidence.

## Model family and inputs
Three separate LightGBM binary classifiers (24/48/72h), each with train-only median imputation and a disjoint Platt calibrator. Logistic Regression with train-only scaling is the executed baseline. The primary bundle is `artifacts/models.joblib`; only load trusted bundles. Static clinical, causal body-stream, environmental and first-72h personal baseline features are included. Patient ID, city name, time/index, event flags and labels are excluded from model inputs.

Labels indicate new stochastic synthetic onset in `(t,t+h]`. Active episodes/onsets, baseline warm-up and insufficient follow-up are excluded from training/evaluation. The simulator is not medically validated; no clinical exacerbation definition is implemented.

## Training and calibration
Seed2026; fixed hyperparameters; no hyperparameter search. 14605 sampled train rows from72 patients; 1377 calibration rows from24 other patients; 4699 test hours from24 further patients at later calendar dates. ≥72h purges keep label windows apart. All preprocessing fits on training only; personal baselines precede fitted states. Patient-hour clustering is retained at test time.

## Actual performance
| Model | Horizon | AUROC | AUPRC | Brier |
|---|---:|---:|---:|---:|
| LightGBM | 24h | 0.6916 | 0.0882 | 0.0279 |
| LightGBM | 48h | 0.6144 | 0.0968 | 0.0557 |
| LightGBM | 72h | 0.3951 | 0.0593 | 0.0853 |
| LogisticRegression | 24h | 0.6619 | 0.1993 | 0.0260 |
| LogisticRegression | 48h | 0.6285 | 0.1841 | 0.0537 |
| LogisticRegression | 72h | 0.6253 | 0.2281 | 0.0800 |

Full metrics and all ablations are in [evaluation.json](../artifacts/evaluation.json). Patient-cluster bootstrap intervals are descriptive and unstable with only5 test-window onsets. Zero of5 held-out onsets meet the72h ≥.35 early-alert rule; median lead time is undefined. All primary models have zero sensitivity at the fixed .35 threshold. LR is stronger than the primary at72h; no consistent environmental/personalization improvement is established.

## Calibration audit — critical limitation
{
  "24": {
    "slope": 0.5808446759257905,
    "intercept": -0.7546591225968994,
    "direction_preserving": true
  },
  "48": {
    "slope": 0.06609886273186515,
    "intercept": -1.8265741858925215,
    "direction_preserving": true
  },
  "72": {
    "slope": -0.2766156047088441,
    "intercept": -2.2464360243374,
    "direction_preserving": false
  }
}

The 72h negative calibration slope reverses raw tree score direction. It is preserved and exposed rather than silently corrected after inspecting test results. Native TreeSHAP explains raw tree log-odds; do not interpret a positive contribution as a calibrated risk increase at72h. This instability blocks clinical interpretation. Independent horizons can be non-monotonic. The demonstration thresholds low<.15/elevated<.35/high≥.35 are not clinical cutoffs.

## Explainability and scenarios
Native LightGBM TreeSHAP contributions are additive in uncalibrated log-odds, checked in tests. If a non-tree primary is used, reference perturbations are explicitly labelled a non-additive fallback, not SHAP. Scenario outputs hold physiology constant, recompute features from past plus projected assumptions, and use these same fitted models. They are conditional associations, not causal treatment/exposure/adherence effects.

## Data limitations, fairness, privacy
120 synthetic profiles and 263 artificial onsets over60 days;4 shared ambient city series. No representative Indian COPD population, subgroup validity, real-device error model, adjudicated outcomes or safety cutoffs. Apparent sex/age fields do not constitute a fairness study. Historical ambient products may be revised and are not verified as-issued operational feeds. All patient data synthetic; real clinical validation requires approval, consent and new held-out data.

## Reproducibility and provenance
Dataset SHA-256: `a9fddac47dfd28548feb336564928b7510b13d35d89a845727b12a54b3e54a5d`. Rebuild with generation → training → demo selection → metric verification commands in the README. Cache license/attribution: [DATA_PROVENANCE.md](DATA_PROVENANCE.md). Model artifact license: MIT; no warranties. Model/code version is a reproducibility label, not regulatory authorization.
