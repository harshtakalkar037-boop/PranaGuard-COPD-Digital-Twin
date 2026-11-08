# Executed v3 verification

These are software/reproducibility checks, **not clinical validation**. The v3 synthetic study passed its predeclared gates; prior v2 remains rejected. No scientific gate, seed, selected model or cutoff was retuned during software fixes.

## Working application

- **119 backend tests passed** in13.67s: original/API/replay/alerts/scenarios, enhanced workflows, previous rejected study, new feature causality/baseline/target isolation, imputation, exact calibrated TreeSHAP, frozen-source/audit metrics, saved-version inference, unsupported states, missing/failed-gate fail-closed behaviour and unchanged legacy outputs. Evidence: `verification/backend-tests.xml` and `.txt`.
- **50 frontend tests passed** in14.87s:14 original,22 enhanced,4 prior-study and10 version-aware v3 tests. Evidence: `verification/frontend-tests.json` and `.txt`.
- **Production TypeScript/Vite build passed** in5.29s; existing theme/components/CSS retained. Evidence: `verification/build.txt`.
- Pinned FastAPI/Starlette emits a non-failing httpx deprecation warning. No unrelated dependency upgrade was made.

## Actual Chromium

- **19 v3/read-only regression checks passed**, no JS/console/API failure or external browser assets. Real local API/model inference, correct48h version/state/probability, matching calibration-rescaled native TreeSHAP, inspectable features/imputation, unchanged24h/72h explanations, scenario boundary, original72h negative result, new audit/all gates/six candidates/uncertainty, visible previous v2 rejection, preserved theme/font and390px/table responsiveness, registry/device navigation,4-city offline fallback, unchanged saved v1 state/history. Evidence: `verification/BROWSER.json` and `browser-v3.txt`.
- **18 original browser workflow checks passed**: search/versions/export, real scenarios, diagnostics, replay/WebSocket start-pause, actual original72h false-positive alert, acknowledgement/action/resolution/reload, status and mobile. These intentional demo writes/resets ran against a **disposable copied SQLite file**, never the shipped/source DB. Screenshots/reports were redirected to the new verification folder; historical screenshots were not overwritten. Evidence: `verification/original-regression/browser-verification.json` and `original-browser-regression.txt`.
- Four latest desktop/mobile patient/study images are retained under `verification/screenshots`. Redundant original-regression screenshots are omitted from the compact archive, not falsely claimed as newly preserved full media.

## Exact science/persistence reproduction

`python -m scripts.verify_model48_v3 --full-audit --bootstrap` executed successfully at2026-11-05T15:37:20.922502Z:

-45,941 fresh-audit predictions and4,699 previously disclosed historical predictions replayed from the actual frozen model and raw records; maximum probability error9.71445146547012e−17.
- Saved metrics/confusion matrices/all gates and300 paired patient-cluster bootstrap intervals reproduced.
-26 protected original scientific files,16 previous-study files and4 pre-fit v3 source hashes verified.
- Original SQLite table digests preserved:120 patients,3,000 states; meta/replay cursor, alerts, interventions and scenarios unchanged. Integrity/FK checks passed.
- Previous v2 remains `GATE_NOT_PASSED`; the original model/environment/generator and original results remain unchanged.

Evidence: `verification/REPRODUCTION.json`, `reproduction.txt`, locked protocol and fitted `FROZEN.json`/`AUDIT.json`. Reproduction is not a second new audit or retuning.

## Fresh installation — PASS

Completed **2026-11-05T15:51:44.819409Z**,71.202s:

- Separate source copy, fresh virtual environment and pinned requirements, `pip check`, fresh `npm ci`.
- Python3.13.16, Node20.20.2, npm10.8.2.
- Bootstrap without reset, actual FastAPI lifespan/ASGI requests and original/v3 fitted inference, rejected-v2 evidence,120/3,000 preserved, additive migrations,4-city offline fallbacks and disabled email verified.
- **119 backend tests +50 frontend tests + production frontend build passed.**
- **118 application-source files hashed and matched** between tested copy and packaged source. No Git clone/reset was substituted for the edited source; no training/new audit generation was run in this clean-install check.

Evidence: `verification/CLEAN_SETUP_VERIFICATION.json`, `clean-setup.txt`, `clean-driver.txt`, `clean-backend-tests.xml`, `clean-frontend-tests.json`.

## Cold compact-source reproduction — PASS

The compact source copy omitted both research audit raw CSVs and historical media, while preserving all118 tested application files and original runtime assets. Using the fresh requirements-only venv:

- `--full-audit --regenerate-audit --bootstrap` **actually regenerated the exact recorded seed31006**,345,600 rows/240 patients, matched raw SHA256 `d8bf42a363efd28eb2b6a8b11bd2cc5223bf4cee8e9fbac346ccf88ee30d2e1a`, then reproduced45,941+4,699 predictions/metrics and300 intervals. Maximum probability error again9.71445146547012e−17.
- **119 backend tests passed** again in13.25s without the previous v2 raw audit file.
- Actual compact-copy ASGI startup, v3 inference, registry, original120 patients, legacy API and previous v2 rejection verified.
- This is reproduction of a known cohort, not a fresh held-out result. No refit or threshold change.

Evidence: `verification/COLD_COMPACT_REPRODUCTION.json`, `cold-compact-reproduction.txt`, `compact-backend-tests.xml` and `.txt`. The new raw research files remain optional/reproducible; they are not needed at runtime.

## Initial software failures retained

- Initial TypeScript build required adding the existing MetricCard icon prop to two new cards. No model or design-system change was involved.
- First backend run:117 passed/1 failed because a new test attempted to write NaN into an int64 pandas test column. The test was corrected to replace the whole columns; model imputation was not changed. Logs/XML retained as `backend-initial-fixture-failure.*`.
- First v3 browser harness stopped after13 checks because it tried to inspect a device-association form before selecting a patient. The harness now makes the existing required selection; no auto-start/auto-selection bypass was added. Log retained as `browser-v3-initial-harness.txt`. Final19 checks passed.

## Distribution checks and nonclaims

`DISTRIBUTION_MANIFEST.json` maps current archive content, deliberate compact omissions and hashes. Byte-level ZIP CRC/safe-path/file-hash/SQLite/source-matching checks and final extracted-archive smoke are recorded in the companion `.zip.verification.json`/`.sha256`. Prior full ZIPs and original workspace DB hashes are checked unchanged. No dependencies, actual `.env`/credentials, temporary DBs or SQLite sidecars are bundled.

Not claimed: clinical validity/benefit, real patient data, physical hardware, a new provider availability check, external email delivery or deployment. The earlier genuine provider evidence remains dated historical evidence; v3 is not a new provider integration. Read [results](RESULTS.md), [model card](MODEL_CARD.md) and [compact/compatibility guide](UPGRADE_GUIDE.md).
