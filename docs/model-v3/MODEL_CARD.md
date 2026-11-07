# pg48-v3-multiseed: experimental synthetic 48-hour model

**Purpose:** demonstrate a separately versioned engineering improvement after the disclosed failed v2 study. No clinical use, diagnosis, emergency alerts or treatment recommendations. This is a modest improvement, not a reliable warning system.

## Inputs and fitted estimator

Selected `tree_context15`: median imputation fitted only on training rows, LightGBM 350 trees, learning rate 0.04,15 leaves, depth 5, minimum 180 child samples, L2=15, deterministic seed 31000,2 threads.48 inputs include first 72h patient-baseline-normalized strictly trailing6/24/72/120h body signals, 24/72h past changes, 72/144h peaks/minima/ranges, adherence/activity, FEV1/prior synthetic exacerbations, and original **historical** ambient context. The descriptive standardized body-deviation mean is not the generator's hidden latent burden and is not a handcrafted prediction. All estimator parameters/features were fixed before training in the protocol.

No event/onset/refractory truth, latent burden, future observations, patient IDs, labels, timestamp/hour or current live weather enter the feature vector. Eligibility is the unchanged original forecasting-state mask. Feature-causality and target-mutation tests are executed. Imputation uses fitted training medians. Baselines use only that patient's first 72h, never future statistics. Input quantization to float32 is shared by development, audit and runtime. Original feature/model sources are not changed.

## Development and audit

Unmodified original generator, 60 days per seed.640 training patients across seeds 31001/31002;160 selection patients 31003;160 calibration 31004;160 cutoff 31005. Separate patient namespaces and purged time ranges: training hours 72–747, development hours 849–1050. Six predeclared candidates; selected by selection-cohort AUPRC alone, no audit-based tuning or early stopping. Summed calibration log-loss +0.5*(slope−1)^2 with nonnegative slope on independent calibration patients; slope 0.8833145148, intercept−0.1558240793. Separate cutoff patients selected maximum F1 with positive true positives/FPR≤10%; cutoff 0.1607938693 (not a clinical threshold).

Selected pipeline/calibration/cutoff/protocol were frozen at 2026-11-05T15:24:59.931163Z before generating seed 31006. One fresh 240-patient audit at hours 1152–1367:45,941 eligible windows, 3,724 positive, prevalence8.106%. All five predeclared gates passed; full numerical results and bootstrap uncertainty are in [RESULTS.md](RESULTS.md). No audit seed, target rule, generator or acceptance gate was changed in response to its outcome.

## Version boundary

Only the frontend's experimental 48h patient card and 48h explanation use the separate `/api/model48/v3/patients/{id}` route. It recomputes for a selected old saved state without writing a new historical prediction. Original 24h/72h, original stored48h, exports/history, all cohort charts, alerts and what-if scenarios remain v1. Their results must not be attributed to v3. Missing/mismatched evidence/failed gates fail closed; UI fallback is explicitly labelled original v1. Unsupported states return no v3 probability/explanation, not zero. No new/manual/device patient inference or72h baseline bypass is implemented.

## Interpretability

LightGBM native TreeSHAP contributions are multiplied by the positive calibration slope; base is slope×raw base+intercept. Thus sigmoid(calibrated base+sum of all contributions) equals the displayed v3 probability. Contributions are **calibrated log-odds**, not additive probability changes and never causal effects. Normalized inputs are in first 72h baseline SD units, not raw sensor units. Original v1 TreeSHAP retains its original raw-score meaning and 72h negative calibration limitation.

## Limitations

- Every patient, physiological stream and outcome is synthetic. Independent seed-specific patients still share the same generator and original four-city historical weather caches. This is neither external clinical validation nor proof of real-world generalization.
- The v2 attempt failed and remains preserved. This is a second, separate improvement attempt.300 descriptive paired patient-cluster bootstrap intervals do not correct for every development/research-attempt selection.
- Fresh audit point AUROC0.5986 is weak; its improvement interval crosses zero. Window recall14.61%, precision16.40%, FPR6.57% at the selected demo cutoff. Most positive windows are missed. These are not patient/event sensitivity, clinical specificity studies or independent alarms.
- Overlapping hourly windows and event-related clustering make row counts a poor proxy for independent sample size. No clinical subgroup fairness, transportability, reliability, net benefit, emergency workflow or treatment benefit is established.
- Independent horizon models/versions can be non-monotonic. Original 72h AUROC remains below chance; original 0.35-cutoff sensitivity was zero at every horizon.
- Historical cached ambient fields are modelled city context, not personal exposure. Current provider context, new registrations and simulated/manual device streams remain outside inference. No physical hardware has been connected or validated.
- Compact distribution omits reproducible large development/audit raw cohorts and redundant historical media. Original runtime data/artifacts remain bundled; seed 31006 can be regenerated exactly for raw prediction verification. Earlier full archives preserve the prior raw audit/media; see [guide](UPGRADE_GUIDE.md).
