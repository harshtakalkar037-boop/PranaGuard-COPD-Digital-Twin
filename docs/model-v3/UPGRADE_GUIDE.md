# Enhanced v3: use, compatibility and compact distribution

## See the new model

Run the normal README setup. In **Patient twins**, only the48-hour card reads the separately versioned `pg48-v3-multiseed` model. Its original stored v1 score is shown underneath;24h/72h stay original. Selecting a saved state computes v3 using only observations through that state's hour. This is a present-day recomputation, **not** a prediction that was persisted at the old date. History/exports are not backfilled.

In **Risk explainability**, choose **48 hours** for the matching v3 explanation.24h/72h use their original models. All v3 transformed feature values/imputation and calibrated log-odds contributions are inspectable. Sigmoid(base+all contributions) equals the displayed probability. No original raw-logit explanation is attached to a new score.

In **Model validation**, the first tables remain original v1, followed by the separately labelled new240-patient v3 audit and a collapsed historical v2 rejection. Compare original and revised rows within the **same cohort table**; do not compare different cohorts as if identical. The original 72h below-chance result/zero original-cutoff sensitivity and rejected v2 findings remain unchanged.

Only the new GET API returns v3:

```text
/api/model48/v3/study
/api/model48/v3/patients/PG-0071
/api/model48/v3/patients/PG-0071?version=25
```

Legacy `/api/patients/{id}` still returns saved original v1 `risks`, including its old48h value. This compatibility choice preserves all stored states and callers; do not call that old field a v3 output. Cohort charts, snapshot exports, alerts/notifications and scenarios stay v1. V3 has no automatic alert, intervention, online retraining, threshold editor or activation button.

If v3 evidence/model/source hashes do not match, or gates are not passed, the new endpoint returns503; the patient card falls back to **explicitly labelled v1**, never an invented v3 score. Unsupported forecasting states yield null v3 probability/explanation, not a fake zero. New fictional registrations/manual/device observations are unsupported for ML; the first 72h baseline requirement remains.

## Preserve your data

Extract into a new directory. Original source repositories/ZIPs were not edited. Do not overwrite a working SQLite file or invoke reset/bootstrap reset to upgrade. Existing enhanced features use safe additive migrations; this v3 inference needs no new database table and never replaces/edits legacy predictions. The shipped database still contains 120 original synthetic patients and 3,000 original states, with no browser-test registrations, devices, emails or research-audit patients.

## Reproduction without shipping huge raw research cohorts

Bundled: original runtime raw longitudinal data, patients, historical weather/air caches, original fitted models/evaluation/splits/experiments, failed v2 fitted artifact/protocol/results/saved predictions/manifest, and all new v3 source/model/protocol/freeze/audit/saved predictions/tests/reports. All current runtime assets are present.

Not duplicated in this compact ZIP:

1. New v3 development raw/feature matrices for1,120 patients and fresh 240-patient raw audit. Seeds, patient counts, generator/source hashes, windows, feature recipes, raw data hashes, frozen fitted model and final saved predictions are included. No research raw data is needed to run the app.
2. Prior v2 raw audit CSV only. Its small generation manifest/profiles and failed model, numerical reports/predictions remain. For the old v2 raw-replay verifier, restore `data/model48_audit/synthetic_longitudinal.csv.gz` from the previous full archive first; do not label that already disclosed cohort a new holdout.
3. Historical screenshots/presentation media and generated duplicate regression screenshots. Their reports/sources remain historical evidence; full earlier media stays in previously delivered archives. Latest four v3 patient/study desktop/mobile screenshots are retained. Historical Markdown image links and old full distribution manifests may therefore refer to media available only in earlier archives; they are not the current distribution content map.
4. Git/dependencies/builds/venvs, actual `.env`/credentials, caches, disposable verification DBs and SQLite sidecars.

Previous full archive, preserved separately: **PranaGuard-Enhanced-v2.zip**, SHA256 `47f067200123ea693faefb692d48a324cc52de48bfbef454a358b969586b3f80`. Original repositories, Enhanced ZIP and original ZIP also remain untouched. Current `DISTRIBUTION_MANIFEST.json` is authoritative for this ZIP; old full manifests are explicitly historical.

Normal read-only checks (no generation/fitting):

```bash
python -m scripts.verify_model48_v3
```

Full raw-inference and bootstrap replay on a fresh extraction:

```bash
python -m scripts.verify_model48_v3 --full-audit --regenerate-audit --bootstrap
```

This regenerates **exactly the already recorded240-patient seed 31006** into the project `.cache/model48-v3-reproduction` if the original staging cache is absent, verifies the raw hash, reproduces45,941 fresh-audit and 4,699 known-historical predictions and 300 paired patient-cluster intervals. It does not retrain, choose a threshold, change a seed or conduct a fresh study. For this reason it is legitimate reproducibility, not a repeated model-selection audit. Existing staging generation scripts use a sibling `corpus-v3` working cache; no generated raw corpus is under runtime data. Training/audit scripts refuse to overwrite their frozen results.

Optional fresh dependency/source-copy check:

```bash
python -m scripts.verify_model48_v3_clean_setup
```

Browser checks additionally require optional `playwright==1.56.0`, `python -m playwright install chromium`, and running frontend/backend. `scripts.browser_verify_model48_v3` is read-only. The old replay-workflow browser verifier performs intentional demo resets/write actions and should be run only against a disposable backup DB, never a working user DB.

## Limitations

Same-generator synthetic audit gains are not clinical validity. Fresh AUROC0.5986 is weak; at cutoff 0.1608 recall14.6%, precision16.4%, FPR6.6%. Most positive windows are missed. Independent hourly forecasts overlap and are not independent patient/event alarms. No personal exposure, hardware compatibility, treatment effect, emergency service or real-world outcome benefit has been established. Current provider context is separate from ML; all patients/measurements/outcomes remain fictional/simulated.
