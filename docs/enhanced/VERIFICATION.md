# Enhanced edition — executed verification and handover

**Verified 5 November 2026. All evidence timestamps use UTC.** This is software verification of a synthetic research demonstration, not clinical validation.

## Scope and preservation

Work started with the read-only [audit and implementation plan](AUDIT_AND_PLAN.md), then proceeded in the isolated supplied-fork copy based on `95a4e2b00fcb2d9df7210c6b87ecba171a0c4e91`. Neither the original workspace nor either remote repository was modified or pushed. No enhanced deployment or new video recording is claimed.

The delivered SQLite snapshot retains **120 original synthetic patients and 3000 original saved states**. Original patient, state, alert, intervention, scenario and replay-metadata row digests match the pre-edit manifest. Two checksum-versioned additive migrations are applied. The browser's disposable registrations/streams are **not** included in the delivery database.

The original font stack, stylesheet, shared visual components and Tailwind configuration are byte-preserved. New views reuse existing components and palette; sidebar scrolling accommodates the additional navigation entries. There is no replacement design system or external browser asset dependency.

## Executed results

| Check | Actual result | Evidence |
|---|---|---|
| Combined backend tests | **87 passed**: 41 original + 46 enhancement tests; repeated successfully in a fresh virtual environment | [JUnit](verification/backend-tests.xml), [log](verification/backend-tests.txt), [fresh-install JUnit](verification/clean-backend-tests.xml) |
| Frontend component tests | **36 passed**: 14 original + 22 enhancement tests; repeated after the latest genuine fixture capture and in the clean installation | [report](verification/frontend-tests.json), [log](verification/frontend-tests.txt), [fresh-install report](verification/clean-frontend-tests.json) |
| Strict TypeScript + Vite production build | **PASS**, 2208 modules; repeated in clean installation | [build log](verification/frontend-build.txt), [clean-install log](verification/clean-setup.txt) |
| Original Chromium workflow | **18 passed, 0 failed** against the enhanced application using disposable data | [report](verification/original-browser/browser-verification.json), [screenshots](screenshots/original-regression/) |
| Enhanced Chromium workflow | **38 passed, 0 failed**; final report at 14:06 UTC | [report](verification/ENHANCED_BROWSER_VERIFICATION.json), [execution log](verification/enhanced-browser-run.txt), [screenshots](screenshots/) |
| Actual external providers | **8/8 current provider components live**: air and weather for Pune, Mumbai, Delhi and Bengaluru; backend routes HTTP 200; genuine retrievals at 14:03:55–56 UTC, provider-valid time 14:00 UTC | [report](verification/LIVE_PROVIDER_VERIFICATION.json), individual `live-context-*.json` files |
| Offline fallback via actual API + Chromium | **4/4 cities PASS**, both components explicitly historical; original values/dates preserved, four unavailable metrics per city remain null; no browser/API errors | [report](verification/OFFLINE_FALLBACK_VERIFICATION.json), [log](verification/offline-fallback-run.txt), `offline-context-*.json`, `screenshots/offline-*.png` |
| Frozen science/design regression | **PASS**: 26 protected file hashes and 73 historical documentation/script files unchanged | [report](verification/INTEGRITY_VERIFICATION.json), [log](verification/integrity-run.txt), [baseline](BASELINE_MANIFEST.json) |
| Frozen held-out predictions | **4699 rows × 3 horizons** match saved predictions; maximum absolute difference **9.71445146547012e-17**, below the 1e-14 check; original metrics and confusion matrices unchanged | [report](verification/INTEGRITY_VERIFICATION.json) |
| Migration/persistence protection | **PASS**, original table row counts/digests unchanged; no foreign-key violations; original workspace database hash unchanged | [initial migration proof](verification/MIGRATION_PRESERVATION.json), [final proof](verification/INTEGRITY_VERIFICATION.json) |
| Genuine clean setup | **PASS**: fresh venv, pinned pip installation, `pip check`, `npm ci`, bootstrap **without reset**, actual ASGI lifespan/API/frozen-model smoke test, 87 backend tests, 36 frontend tests, strict production build | [report](verification/CLEAN_SETUP_VERIFICATION.json), [complete log](verification/clean-setup.txt), [run log](verification/clean-setup-run.txt) |

Clean setup used **Python 3.13.16, Node 20.20.2, npm 10.8.2**, a separate ZIP-style source copy, and newly installed dependencies. It was not a clone of the unmodified base commit: the report records the hashes of **94 actual enhanced application/configuration/test files**. The delivered archive is checked against these hashes. The clean smoke check read ten original/enhanced endpoints plus all four city contexts, verified the original cohort and frozen predictions, and checked preservation before and after startup. It did not reset the delivery database.

One non-failing upstream warning remains: Starlette's TestClient warns that its `httpx` integration is deprecated. The pinned original stack was retained instead of introducing an unrelated dependency change. No dependency-vulnerability audit or production security certification is claimed.

## What the workflow checks exercise

- Search, empty state, fictional-identity confirmation, validated registration, unique backend ID and persistent profile/export.
- Manual baseline references do not bypass the 72-hour gate. Simulated/manual monitoring does not fabricate 24/48/72h probabilities.
- Persistent symptoms/adherence and review notes, original care-ledger integration, linked notifications and browser reload.
- All **four generic simulated device types** associated, explicitly started, ingested through the then-current authenticated backend endpoint (historical run; the simulator now uses the same validated service in-process), stopped, and inspected. Stopped streams do not continue generating readings. Actual stored readings drive trends and immutable monitoring versions.
- Device/patient mismatch, capabilities/units/ranges/time validation, request/event idempotency and conflicts, token checks, admin protection, stale/error/restart behavior, migration checksums and safe persistence are exercised by backend tests.
- Notification patient/category filters, test event, unread/read independence, active→acknowledged→under_review→resolved→closed lifecycle and append-only review history.
- Disabled email records `not_sent_disabled`. The backend suite also performs **actual localhost SMTP socket capture** with a configured demo recipient. It tests privacy, disabled/preview/failure/rate-limit behavior. Local SMTP acceptance is not external inbox delivery.
- Genuine current city context and explicit timestamps/attribution; dedicated record-level provenance, classifications, missingness and exports.
- Original model twin/features/probabilities unchanged after enhanced monitoring activity. Desktop and 390px mobile views retain the original theme without horizontal overflow. Actual patient-profile and device views are opened on mobile; provenance filters are exercised.
- No external browser assets, JavaScript/console errors or failing browser API calls in the successful integration runs.

Provider-failure, malformed/stale-response,HTTP 429, cache TTL, persistent retry/backoff and missing-cache cases are tested using explicitly labelled controlled test transports. Those are **not** represented as real provider successes. Conversely, `LIVE_PROVIDER_VERIFICATION.json` comes from actual network-backed backend execution, not those doubles.

## Offline proof and data boundaries

With `PRANAGUARD_LIVE_ENV_ENABLED=false`, the delivery database has no current-provider cache. All four cities therefore use the original hash-verified historical files. Valid time remains **29 September 2026, 23:00 UTC**, with the original **18 October 2026** retrieval timestamps. U.S. AQI, weather code, wind speed and wind direction were not in those historical sources; their values remain **null**, not zero or invented estimates.

The dated live JSON evidence and frontend test fixtures are documentation/testing only. They are not a hardcoded production fallback, a station observation, a physical-device observation or patient exposure. Current context is Open-Meteo/CAMS **modelled city-grid data**. Its AQI is **U.S. AQI, not Indian CPCB NAQI**. Current context, manual registration values and simulated readings never enter the frozen feature pipeline, calibration or TreeSHAP calculations.

## Reproduce safely

Install and start the app using the [README](../../README.md#12-run-locally). Do not run research generation/training or reset commands to install this edition.

From the project root, after activation of the normal environment:

```bash
python -m pytest
npm --prefix frontend test
npm --prefix frontend run build
python -m scripts.verify_enhancement_integrity
```

The integrity script reads SQLite in read-only mode and performs prediction checks only; it does not retrain or rewrite the evaluation. Git-history comparison runs when the original isolated Git metadata is present; a downloaded ZIP has no `.git`, so the 73-history-file comparison is a recorded development check, not rerunnable there. Protected-file, saved-prediction, metric and preserved-database checks remain rerunnable. The sibling-original-workspace hash comparison is likewise conditional on that workspace existing.

To repeat the genuine fresh-install check (requires network access to the package registries):

```bash
python -m scripts.verify_enhanced_clean_setup
```

It creates an isolated sibling `.cache/pranaguard-enhanced-clean-setup` source copy and its own dependencies; it never invokes reset/training or modifies the source database. It refuses to delete an existing destination that it did not previously create. Historical `scripts/verify_clean_setup.py` is retained unchanged for the old submission and should **not** be used as the enhancement verifier.

### Optional actual browser checks

Browser automation is an optional verification dependency, not required to run the application:

```bash
python -m pip install playwright
python -m playwright install chromium
```

For mutation-heavy integration checks, use a **new throwaway database**, never the shipped working snapshot. Start a separate backend configured as below, then Vite in a second terminal:

```bash
# Repository root; do not run another backend on this port at the same time.
PRANAGUARD_DB="$PWD/data/browser-check.sqlite" \
PRANAGUARD_LIVE_ENV_ENABLED=true PRANAGUARD_EMAIL_MODE=disabled \
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Second terminal
npm --prefix frontend run dev

# Third terminal, repository root and venv active
python -m scripts.verify_live_environment
python -m scripts.browser_verify_enhanced
```

Live verification records the actual live/cache/fallback statuses; provider availability is external and a future run is not guaranteed to obtain current values. The enhanced browser verifier refuses enabled external email mode. Rerunning it creates additional fictional test records and waits for the demo email test's cooldown when necessary. Browser-captured fixtures are actual synthetic local API responses; frontend mutation tests are explicitly labelled component-test doubles.

To repeat the **read-only offline** check, use the unchanged preserved database, with no current cache, and run the backend with `PRANAGUARD_LIVE_ENV_ENABLED=false` and email disabled. With Vite running:

```bash
python -m scripts.browser_verify_offline
```

The original 18-check historical browser verifier performs replay/reset actions. Its development run was restricted to the disposable verification database; **do not run it on the preserved delivery database**.

## Remaining limitations — not hidden by passing tests

- No real patient records or physical hardware were used. Bluetooth/USB/brand-specific integrations, medical-device certification and production enrollment are not implemented.
- New-patient readiness requires 72 distinct first-window hourly bins for core signals **and actual 72-hour observed elapsed span**. The integration run did not wait 72 hours or claim that a patient completed warm-up; clock-controlled unit tests exercise the gate. A device-only baseline still lacks the full compatible evaluated feature frame, so new-patient inference remains unsupported even after baseline collection. No manufactured predictions are supplied.
- SMTP credentials or externally verified inbox delivery were not supplied/tested. The commercial Open-Meteo customer/key branch is not verified. CPCB/Data.gov.in and IMD are not integrated; see [provider investigation](PROVIDER_INVESTIGATION.md).
- The free provider is non-commercial and rate/availability constrained; current context defaults off. Backoff/caching do not provide a service-level guarantee.
- The existing 72h LightGBM AUROC remains **0.3951**, below chance. All horizons have **zero sensitivity at 0.35**. There is no demonstrated clinical validity/benefit. What-if changes are noncausal; raw-score TreeSHAP is not a calibrated-probability decomposition.
- Read endpoints remain public in this demo; the optional shared write token and per-device HMAC are not production identity/RBAC, consent or regulated security. Use synthetic data only.
- Simulations intentionally stop after backend restart. No distributed replay coordination, automatic clinical intervention, emergency response or enhanced remote deployment is claimed.

## Archive handover

`PranaGuard-Enhanced.zip` contains source, tests, setup configuration example, guides/evidence/screenshots, the unchanged scientific artifacts/historical deliverables, and the safely backed-up preserved SQLite snapshot. `DISTRIBUTION_MANIFEST.json` records per-file SHA256 hashes; its own self-hash is intentionally omitted. A companion `.zip.sha256` file authenticates the final ZIP bytes against accidental corruption, not publisher identity.

The archive excludes `.git`, dependency environments, `node_modules`, generated builds/caches, all actual `.env` files, disposable verification databases and SQLite sidecars. No API/SMTP credentials or device bearer tokens are included. Use the fictional registry to create your own demo records; the delivery does not prepopulate the browser's trial registrations.
