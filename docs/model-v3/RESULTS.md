# Completed v3 results — modest experimental improvement

The earlier v2 study remains **GATE_NOT_PASSED** and inactive. The repeated user request initiated a separately predeclared, larger-cohort v3 study; no previous test is relabelled pristine. Every patient/outcome is synthetic.

## Fixed design

- 640 training patients (seeds 31001/31002), 160 selection(31003), 160 calibration(31004), 160 cutoff(31005). Six fixed candidates, selected solely by separate selection-cohort AUPRC.
- Training hours 72–747 and development849–1050, stride3, patient/seed-disjoint; first 72h baselines and strictly trailing features, no hidden/event/future predictors.
- Fitted model/calibrator/cutoff/protocol frozen **2026-11-05T15:24:59.931163+00:00** before seed 31006 generation. One fresh 240-patient audit 1152–1367, all eligible hours. Generator, environment caches, original pipeline and acceptance gates unchanged.

| Partition | Patients | Eligible sampled windows | Positive windows |
|---|---:|---:|---:|
|train|640|128608|11615|
|selection|160|9616|834|
|calibration|160|9527|885|
|threshold|160|9340|910|

## Development selection

| Candidate | Selection AUPRC | Selection AUROC |
|---|---:|---:|
|tree_original35|0.141190|0.572008|
|linear_core8|0.143308|0.611806|
|tree_body15|0.137485|0.577956|
|tree_context15 **selected**|0.144375|0.586774|
|tree_context31|0.129128|0.564272|
|tree_body7|0.141175|0.583227|

Selected `tree_context15` uses48 features. Independent constrained calibration slope 0.8833145148, intercept-0.1558240793; independently selected demo cutoff 0.1607938693. No audit-derived tuning.

## Primary fresh 240-patient audit

45,941 eligible hourly forecasts, 3,724 positive windows; prevalence8.1060%. Both models are scored on the exact same rows.

| Metric | Original 48h | v3 experimental 48h |
|---|---:|---:|
|AUROC ↑|0.55786433|0.59862081|
|AUPRC ↑|0.11011285|0.14018107|
|Brier ↓|0.07556857|0.07355143|
|Log loss ↓|0.28721357|0.27654279|
|Window recall|0.00000000|0.14607948|
|Precision|0.00000000|0.16395419|
|False-positive rate|0.00000000|0.06570813|
|Mean probability|0.11650492|0.09288131|
|Operating cutoff|0.35000000|0.16079387|

AUPRC point increase is27.31% relative. This is **not** an accuracy/clinical-benefit claim. The new model still misses85.39% of positive windows at its selected cutoff, with precision only 16.40%. Correlated hourly windows are not independent patient/event alarms.

- Original confusion matrix: `[[42217, 0], [3724, 0]]`.
- V3 confusion matrix: `[[39443, 2774], [3180, 544]]`.
- At the identical old0.35 cutoff, v3 recall is0.02013963, precision0.50335570, FPR0.00175285; original remains zero recall. Ranking/Brier improvements are not obtained merely by lowering a cutoff. The different operating-point cutoffs are not medical thresholds.

## Predeclared decision

- **PASS** — auprc 10 percent relative improvement.
- **PASS** — auroc not worse.
- **PASS** — brier not worse with 0 0001 tolerance.
- **PASS** — nonzero recall at validation selected threshold.
- **PASS** — false positive rate at most 15 percent.

**EXPERIMENTAL_GATE_PASS**: available only as the separately labelled synthetic 48h display/API/explanation. No original stored predictions, 24h/72h, histories, scenarios or alerts were replaced. This is not clinical promotion.

## Uncertainty and multiple attempts

300 paired patient-cluster bootstrap resamples (fixed seed 20261106); descriptive95% intervals, revised minus original:

- auroc: [-0.01601525, 0.09670325].
- auprc: [0.00059367, 0.06537701].
- brier: [-0.00380169, -0.00046392].

AUROC-improvement interval crosses zero. AUPRC and Brier intervals favour v3 on this cohort, but they do not correct for all candidate/research-attempt selection. V2 failed; this second attempt is separately disclosed, not a guarantee that repeated searching produces generalization. Same-generator/weather synthetic patients are not clinical/external validation.

## Known original test — secondary only

The4699-row original test was disclosed before v3, not used for development and not a pristine new audit. Do not headline its stronger result as fresh clinical evidence.

| Metric | Original | v3 |
|---|---:|---:|
|auroc|0.61437694|0.75268165|
|auprc|0.09675618|0.18227202|
|brier|0.05573064|0.05087812|

## Fingerprints and software verification

- Protocol SHA256: `9535446b679290721bcf70906d8ee00a239e187508c2ac46a3ca45d9a50f283e`.
- Frozen model SHA256: `35cbe7b0deda11e0caaba55bb00ba3f519a5f28625900024e2f82b2f08c27d0a`.
- Unchanged generator SHA256: `f49ae916428c8607a74186305263742d5f130c0ebbe8a228b940ddb22ee79c02`.
- Fresh raw audit SHA256: `d8bf42a363efd28eb2b6a8b11bd2cc5223bf4cee8e9fbac346ccf88ee30d2e1a`.

Raw-inference/metric/bootstrap reproduction, original 26-file preservation, prior16-file preservation and original SQLite table digests are recorded in [verification](VERIFICATION.md). Original/v2/v3 evidence is separately version-labelled; no clinical validity or72h-model improvement is claimed.
