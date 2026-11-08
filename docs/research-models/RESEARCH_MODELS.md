# PranaGuard v7 — External Research Models

Additive module. Every existing v6 feature is preserved and the production **PranaGuard Digital Twin** (v1 + 48h v3 audit) is untouched: no retraining, no shared artifacts, no metric mixing, no identity merging with platform patients.

## Model cards (never merged, never ranked)

| | PranaGuard Digital Twin | Cough Analysis | Longitudinal COPD Research |
|---|---|---|---|
| Model id | *(production twin, not in the external registry)* | `cough-copd-rf-calibrated` | `tolife-longitudinal-probe-v2` |
| Dataset | generated synthetic cohort (provenance in Sources) | Cough-COPD(CC), Zenodo 14881818, CC-BY-4.0 | TOLIFE Clinical Study A, Zenodo 23263785 v2.0, CC-BY-4.0 |
| Task | 24/48/72h synthetic-onset risk (v1) + v3 48h audit | binary file-level study-cough classification (COPD vs Healthy labels) | leakage-corrected 24/48/72h exacerbation-onset feasibility probe |
| Inference live in app | yes (production) | yes, WAV/FLAC/OGG upload → calibrated probability (runtime-dependent) | no — report-only research view |
| Evidence class | SYNTHETIC_GENERATED | REAL_OBSERVED recordings → REAL_DERIVED metrics | REAL_OBSERVED inputs → REAL_DERIVED metrics |

These tasks and datasets differ; the UI and API deliberately show metrics **per model only**.

## Model B — Cough Analysis (`/api/models/cough/*`)

- **Pipeline**: mono mix-down → 25 ms frames / 10 ms hop (Hamming) → pre-emphasis 0.97 → 26 log-Mel bands + 13 MFCCs + ZCR/RMS/spectral centroid (features v1, 58 features) → calibrated random forest (train-only sigmoid calibration, cv=5) → calibrated probability + class at threshold 0.5.
- **Inference endpoint** `POST /api/models/cough/infer` (multipart) runs the bundled `cough_model.joblib` (4,570,809 bytes) with identical preprocessing. If the artifact or `soundfile` is unavailable the endpoint returns **503 with an explicit reason** — the platform never fabricates a prediction.
- **Executed evaluation** (publisher train/test split, file-level): AUROC **0.9316**, AUPRC **0.8293** (prevalence 0.262), accuracy 0.872, **COPD sensitivity 0.578 (19/45 COPD files missed)**, specificity 0.976, Brier 0.0987.
- **Explainability**: dataset-level feature attribution computed by this module (mean decrease-in-impurity; top `logmel3_mean` 0.0401, `mfcc2_std` 0.0373). It does **not** reuse the Digital-Twin SHAP implementation, and importance is not causality.
- **Limits** (shown in-app and enforced in tests): no published participant identifiers → participant independence unverifiable, file-level metrics are upper bounds; low sensitivity makes it useless to rule disease out; **not** a diagnostic, screening, triage or treatment tool.
- Raw audio is **not redistributed** in this repository; only the derived model artifact, index of filenames and executed metrics ship.

## Model C — Longitudinal COPD Research (`/api/models/tolife/*`)

Corrected experiment only (v1 probe with leakage is superseded and described as such):

1. Study-model-estimated symptom channels (CAT/CCQ/mMRC classes) were **removed from predictors and from the rendered research view**; only observed sensor/clinical channels are shown.
2. Strict in-frame event audit with reconciled counts: 80 register entries → 42 unique participants, 0 missing dates; 42 in observed frame, 32 with any valid measurements in the prior 7 days, **30 evaluable** (in-frame with prior-7d measurements). Reasons are shown per event.
3. Metrics recomputed with leave-one-participant-out folds, prior-day-only features, fixed 24/48/72h horizons, AUROC with bootstrap CI, AUPRC-with-prevalence, Brier:

| Horizon | AUROC [CI] | AUPRC (prev) | Brier | Positive days |
|---|---|---|---|---|
| 24h | 0.355 [0.233–0.472] | 0.0020 (0.0025) | 0.191 | 18 / 7,195 |
| 48h | 0.389 [0.244–0.543] | 0.0052 (0.0054) | 0.213 | 39 / 7,195 |
| 72h | 0.393 [0.276–0.523] | 0.0064 (0.0078) | 0.218 | 56 / 7,195 |

These are **at-or-below-chance feasibility results** and are presented as such; they are not a deployable early-warning capability. The horizon analysis is limited to 24/48/72h because the corrected pipeline has enough prior-day information for those windows; shorter or adaptive horizons were not manufactured. Longitudinal series panel: 42 in-frame onsets, median/IQR of observed channels relative to onset day; participant identities are `tolife:…` coded strings only.

## API surface (additive; no collisions with existing routes)

```
GET  /api/models/registry                 registry rows (id, version, dataset, task, features, preprocessing, artifact, metrics, limitations, evidence class)
GET  /api/models/cough/info               executed metrics + dataset + limitations + inference availability
POST /api/models/cough/infer              multipart audio → calibrated probability (503 with reason when unavailable)
GET  /api/models/cough/attribution        own global feature importance (not SHAP)
GET  /api/models/cough/history            persisted inference audit log
GET  /api/models/tolife/overview          reconciled event audit + corrected horizon metrics
GET  /api/models/tolife/series            42 in-frame longitudinal series
GET  /api/models/tolife/participants      86 coded participant rows
```

## Persistence — migration `006_research_models.sql` (additive, idempotent)

`model_registry`, `model_predictions` (cough inference audit), `experiment_runs`, `research_cough_recordings` (853-row index of filenames/classes/splits only), `research_tolife_participants` (86), `research_tolife_events` (80 register events with audit flags), `research_evaluation_metrics`. The `research_seed_v7` meta key makes seeding one-time; existing v6 tables and data are untouched.

## Explainability separation

Digital Twin: LightGBM native TreeSHAP (unchanged, v6). Cough: own impurity-based importance. TOLIFE: none (report-only). Cross-model reuse is forbidden by test (`test_cough_attribution_is_own_importance_not_shap`).

## Home-screen provenance rule

The landing view carries no "Synthetic" or "External model" banner. Provenance is disclosed where it belongs: the Sources page, the sidebar safety card, model info panels, the registry, and this document — with natural names (PranaGuard Digital Twin, Cough Analysis, Longitudinal COPD Research).
