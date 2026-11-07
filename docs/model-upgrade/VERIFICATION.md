# Latest model-study build — executed verification

**Date: 5 November 2026.** Passing software checks are not evidence that the rejected model improved.

## Separate decisions

- **Software/package:** checks below pass.
- **48h model promotion:** **NOT PASSED**. The fresh-cohort candidate had worse AUROC, AUPRC and Brier. The original inference/cutoff remains active. See [actual results](RESULTS.md), [locked protocol](PROTOCOL.json) and [complete evaluation](../../artifacts/model48_v2/AUDIT_EVALUATION.json).

## Actual executed checks

| Check | Result | Evidence |
|---|---|---|
| Combined backend suite | **101 passed** = original41 + enhancement46 + model-study14 | [JUnit](verification/backend-tests.xml), [log](verification/backend-tests.txt) |
| Frontend component suite | **40 passed** = original14 + enhancement22 + model-study4 | [report](verification/frontend-tests.json), [log](verification/frontend-tests.txt) |
| Strict TypeScript/Vite build | **PASS**,2209 modules | [build](verification/frontend-build.txt) |
| Actual read-only Chromium/API checks | **13 passed,0 failed**, desktop and390px mobile; rejected status, metrics, all8 candidates, failures/uncertainty, original48h TreeSHAP, unchanged probabilities/history, no JS/API errors/external assets | [report](verification/BROWSER_VERIFICATION.json), [log](verification/browser.txt), [screenshots](verification/screenshots/) |
| Saved prediction/metric reproduction | **PASS**,23278 fresh-audit rows and4699 historical rows, both original and rejected fitted models; max absolute error9.71445146547012e-17 | [report](verification/REPRODUCTION_AND_PRESERVATION.json), [log](verification/reproduction.txt) |
| Scientific/design/persistence protection | **26 original protected file hashes unchanged**; original120 patients/3000 states and original table digests unchanged; no foreign-key violations | [report](verification/REPRODUCTION_AND_PRESERVATION.json), [pre-enhancement baseline](../enhanced/BASELINE_MANIFEST.json) |
| Genuine clean installation | **PASS**: new venv, pip installation/check, npm ci, no-reset bootstrap, real ASGI/model/API smoke, original cohort persistence, all4 offline cities, inactive candidate; **101 backend +40 frontend tests**, production build | [report](verification/CLEAN_SETUP_VERIFICATION.json), [full log](verification/clean-setup.txt) |
| Clean-source identity | **105 application/configuration/test files** hashed, source copy identical before/after clean installation; ZIP checked against the same map | [report](verification/CLEAN_SETUP_VERIFICATION.json) |

The clean run used Python3.13.16, Node20.20.2 and npm10.8.2. No model was retrained or retuned during software/clean-install checks. Original replay/scenario/alerts, monitoring/registration, device simulation, notification/email and environment tests are included in the combined suite. Earlier18-original/38-enhanced browser reports remain in `docs/enhanced/verification` as historical results of that edition; they were not relabelled as new browser runs.

The initial clean-install attempt completed dependency installation and startup/preservation checks, then pytest exited by SIGKILL(-9) without an assertion traceback or completed JUnit report while several preview servers were running. The sandbox has approximately2GB RAM; resource pressure is suspected, not independently proven. We stopped preview servers and repeated the complete fresh install successfully in69 seconds, with no model/data/threshold changes. Initial evidence and the retry note are retained in `verification/clean-setup-initial-killed.*` and `CLEAN_SETUP_RETRY_NOTE.txt`.

Non-failing dependency notices remain: Starlette TestClient's `httpx` deprecation, Recharts2's maintenance warning and the transitive whatwg-encoding deprecation. The original dependency stack was retained; no vulnerability/security-certification claim is made.

## Reproduce the current build

Use [README setup](../../README.md#12-run-locally) from extracted `PranaGuard-Enhanced-v2.zip`. Do not reset, regenerate data or train to install it.

```bash
python -m pytest
npm --prefix frontend test
npm --prefix frontend run build
python -m scripts.verify_model48_study
```

Reproduction performs fitted inference and metric/preservation checks only. For an isolated clean installation with fresh dependencies:

```bash
python -m scripts.verify_model48_clean_setup
```

This creates a separate sibling cache copy and its own venv/node_modules. Use adequate free memory and stop unused large preview servers first. It never resets the working database, retrains a model, generates a new audit or sends external email.

For the optional browser checker, install Playwright and Chromium, start the normal backend/frontend, then:

```bash
PRANAGUARD_BROWSER_URL=http://127.0.0.1:5173 \
PRANAGUARD_API_URL=http://127.0.0.1:8000 \
python -m scripts.browser_verify_model48
```

Browser checks are read-only, use existing120 synthetic profiles, and verify that reading the study does not alter the original twin/history. They do not activate the candidate.

## Handover and boundaries

The ZIP contains all previous enhancement features plus the completed rejected study, separate120-patient synthetic audit data, trained research artifact, saved predictions, scripts/tests, documentation and an evidence panel at the bottom of **Model validation**. The audit patients are not imported into the active SQLite registry. The original artifacts and prior delivered ZIPs are not overwritten.

`DISTRIBUTION_MANIFEST.json` records content hashes; its self-hash is intentionally omitted. The final ZIP also has a companion SHA256 file. Packaging checks include archive CRC, safe/unique relative paths, excluded credentials/dependencies/builds/disposable databases, matching clean-tested source, protected artifacts and SQLite integrity/digests. The final extracted archive is smoke-tested with the freshly installed dependencies.

No improved active model, clinical accuracy, real hardware, external email delivery, clinical intervention, emergency response or remote deployment is claimed. New-patient inference remains unsupported without the mandatory72h coverage and full compatible evaluated features. Current environmental context remains separate from ML inputs.
