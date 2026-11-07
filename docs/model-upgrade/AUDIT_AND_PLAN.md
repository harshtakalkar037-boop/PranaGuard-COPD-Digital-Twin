# 48h model update — audit and predeclared plan

The user now authorizes model-improvement research. Work occurs only in an isolated copy of the delivered Enhanced ZIP; the original repositories, previous enhanced copy and original experiment artifacts are unchanged.

## Read-only findings
- Original48h LightGBM: AUROC0.6144, AUPRC0.0968, Brier0.0557, zero recall at0.35. The high fixed threshold and weak ranking are separate issues.
- Only24 original test patients and strongly correlated hourly labels; previously disclosed test results cannot be described as unseen.
- Original35 predictors combine absolute/body/environment/baseline features. Additional patient-relative trailing means can reduce between-patient nuisance variation without using future observations.
- Calibration labels are imbalanced and correlated. The original unconstrained72h Platt slope is negative; the revised48h calibrator will prohibit ranking reversal.
- Training/calibration/test, generator, historical environmental products, native TreeSHAP, replay/SQLite history, enhancements and styling must be preserved.

## Ordered work
1. Record the exact development folds, bounded candidate set, calibration/threshold patients, audit seed, metric gates and uncertainty protocol before fitting. See PROTOCOL.json.
2. Implement separate causal feature/model/research scripts; do not edit original features.py, ml.py, train.py, generator or scientific artifacts. Select only on internal original-training folds.
3. Fit, calibrate, choose demo operating point, freeze/hash; then run one fresh synthetic audit and the known historical benchmark. Report every candidate/development score and all audit results, including failures.
4. Only if predefined gates pass, expose the versioned48h model and explanations through separate read-only API/UI comparison. Never relabel original stored probabilities or legacy alerts as revised outputs.
5. Add causality, separation, reproducibility, calibration, explanation, API, UI and regression tests. Repeat build and clean-install/source/archive checks. Update setup/model documentation and deliver a new ZIP.

No guarantee of clinical usefulness, real-data generalization, or improvement on every metric/patient/horizon is made. Fresh patients share the unchanged synthetic generator and historical weather, so this is not external clinical validation.
