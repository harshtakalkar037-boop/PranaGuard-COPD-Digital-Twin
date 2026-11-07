# 48-hour model improvement attempt — completed, candidate not promoted

**5 November 2026.** The user authorized a model-improvement attempt after the Enhanced edition. This is a new, isolated, explicitly versioned research study; the original experiment, data, fitted models and SQLite history are preserved.

## Bottom line

Eight predeclared candidates were fitted and compared using development data. The selected candidate improved mean internal validation AUPRC, but **failed the fresh synthetic audit**. It was **not activated**. Calling it an improved 48h model or merely lowering the alert cutoff would misrepresent the results.

The latest ZIP adds the completed study, reproducible data/model/metrics, tests and a read-only comparison panel at the bottom of **Model validation**. It does **not** silently replace the existing 48h predictions with a worse model.

## Actual matched-cohort results

Higher AUROC/AUPRC and lower Brier are better. Metrics below are comparisons on the **same rows within each cohort**; never compare the old historical0.6144 directly with the fresh-cohort 0.5494.

| Cohort / model | AUROC | AUPRC | Brier | Sensitivity | False-positive rate | Cutoff |
|---|---:|---:|---:|---:|---:|---:|
| Fresh 120-patient audit — original 48h |0.5539|0.1485|0.0822|0.0%|0.0%|0.3500|
| Fresh 120-patient audit — rejected candidate |0.5494|0.1099|0.0877|10.0%|6.36%|0.2698|
| Previously disclosed original test — original 48h |0.6144|0.0968|0.0557|0.0%|0.0%|0.3500|
| Previously disclosed original test — rejected candidate |0.5946|0.0700|0.0637|8.85%|5.95%|0.2698|

The fresh audit contains **23278 eligible hourly forecasts,2090 positive windows,120 distinct synthetic patients**, seed20261105. The original historical test has 4699 rows. Windows overlap, so neither row count is the number of independent clinical events or people.

The revised cutoff was selected before audit using separate development patients. It produces some positive classifications but also false positives. **Nonzero sensitivity at a different cutoff is not evidence that ranking, calibration or clinical usefulness improved.**

Paired 300 patient-cluster bootstrap 95% intervals for revised-minus-original differences on the fresh audit:
- AUROC: **−0.0694 to +0.0821**.
- AUPRC: **−0.0891 to +0.0144**.
- Brier: **+0.00076 to +0.00952** (positive is worse).

These are descriptive synthetic intervals, not clinical validation or a prospective clinical study.

## What was tried

The [protocol](PROTOCOL.json) and [audit/plan](AUDIT_AND_PLAN.md) were recorded before fitting. Original seed2026 patients PG-0001–0072 and training hours72–747 were the only source for candidate selection/refitting. Three folds separated patient identity and calendar time with at least 72h purge. No current weather, monitoring devices, manually entered registration data, patient IDs, future labels, event-onset fields or hidden generator burden were model predictors.

Candidate development AUPRC (mean across three internal folds):

| Candidate | AUPRC |
|---|---:|
| Original-style35-feature tree refit |0.1313|
| Original35-feature linear |0.1495|
| Patient-relative core linear,C0.03 |0.1945|
| **Patient-relative core linear,C0.3 — selected** |**0.2140**|
| Longer-trend linear,C0.03 |0.2031|
| Longer-trend linear,C0.3 |0.2083|
| Longer-trend linear,C3 |0.2082|
| Regularized longer-trend tree |0.1617|

The selected eight inputs were FEV1,24h mean SpO2/heart-rate/respiratory-rate/symptom deviations from each patient's first 72h baseline,24h sleep deviation,24h adherence and24h historical PM2.5. Baselines and rolling features are causal; imputation/scaling fit on training only.

The selected classifier was fitted once on 14605 sampled training rows. Separate original patients PG-0073–0084 supplied 652 calibration rows; PG-0085–0096 supplied 725 threshold-selection rows. Positive-slope constrained Platt calibration avoids the ranking reversal seen in the original 72h calibrator; it does not guarantee improvement. The cutoff maximized validation F1 subject to at most 10% validation false-positive rate. Its development sensitivity was only 3.03%, an additional warning about limited generalization.

The fitted pipeline, calibration and cutoff were saved and hashed in [FROZEN_DEVELOPMENT.json](../../artifacts/model48_v2/FROZEN_DEVELOPMENT.json) **before** the independent audit cohort was generated. Audit seed20261105 and the acceptance rules were fixed beforehand. There was one audit; no new seed, candidate or cutoff was selected in response to its outcome.

The fresh cohort uses the **unmodified original generator** and historical environmental caches, with separate AUD48- patient identifiers. It therefore tests new synthetic patients/outcomes, not a new disease mechanism, new weather distribution or real-world clinical population. The generator was not rewritten to manufacture a more learnable task.

## Gate outcome

The candidate failed three required checks: 10% relative AUPRC improvement, non-worse AUROC and non-worse Brier. It passed nonzero recall and at-most 15% fresh-audit false-positive rate. **The joint gate failed.**

Original 48h inference, the fixed original 0.35 cutoff,24h/72h models, TreeSHAP, scenarios, alerts, cohort, state versions and historical evaluation remain unchanged. The candidate is retained as a rejected research artifact only. No activate/deploy button or revised patient-inference endpoint is provided.

## Files and reproduction

- `artifacts/model48_v2/model.joblib`: the actual fitted, rejected candidate; never loaded by normal patient inference.
- `artifacts/model48_v2/FROZEN_DEVELOPMENT.json`: all candidate/fold scores, selected feature names, calibration, operating point and pre-audit fingerprints.
- `artifacts/model48_v2/AUDIT_EVALUATION.json`: full results, confusion matrices, ROC/PR/calibration points, bootstrap intervals and failures.
- `artifacts/model48_v2/audit_predictions.csv.gz` and `historical_comparison.csv.gz`: actual saved probabilities/labels, not handwritten risk scores.
- `data/model48_audit/`: separate synthetic cohort, profiles and provenance; not registered into the application's120-patient SQLite cohort.
- `backend/app/model48.py`: separate causal feature, classifier/calibration and exact log-odds explanation implementation. Original`features.py`/`ml.py` are unchanged.
- `scripts/train_model48.py`, `scripts/audit_model48.py`: development/freeze and one-shot audit scripts; they refuse to overwrite completed development/audit files.
- `GET /api/model48/study`: read-only executed evidence; returns`candidate_active:false` and`decision:retain_original`.

After ordinary setup, reproduce saved predictions/metrics **without retraining or retuning**:

```bash
python -m scripts.verify_model48_study
python -m pytest
npm --prefix frontend test
npm --prefix frontend run build
```

The reproduction script reads both source datasets, reruns both fitted models, compares all saved probabilities/metrics, checks protected artifacts and the preserved SQLite table digests, and writes its report only under`docs/model-upgrade/verification`.

Do not delete audit artifacts and repeatedly search fresh seeds until a positive result appears. Any future study must be separately versioned, disclose this failed attempt, predeclare a new design and retain genuinely untouched evaluation data. Repeating software tests is not permission to retune on the completed audit.

## What would support a credible improvement

More representative longitudinal patient data with reliably timed, clinically adjudicated exacerbation outcomes; more independent development/calibration patients; stable out-of-patient/out-of-time validation; explicit missingness/measurement quality; calibration and alert-burden evaluation; and prospective external testing. More synthetic rows alone or a lower cutoff cannot establish clinical usefulness.

All existing limitations remain: synthetic records only, no clinical validity/benefit, original 72h AUROC below chance, original zero sensitivity at0.35, noncausal scenarios, no real-device observations and no real-patient inference. The update does not fix those limitations by renaming metrics or replacing labels.
