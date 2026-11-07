# Testing and QA

Run in a disposable synthetic environment: `python -m pytest backend/tests -q`, `npm --prefix frontend ci`, `npm --prefix frontend test`, `npm --prefix frontend run build`, and `npm --prefix frontend audit --audit-level=low`. CI uses Python 3.13 and Node 20. Browser harnesses in `frontend/e2e` require explicit disposable credentials; several write synthetic test records and must never target production. See [release readiness](FINAL_RELEASE_READINESS.md) and [application audit](COMPLETE_APPLICATION_AUDIT.md) for dated evidence and gaps.

Automated axe and responsive checks do not establish accessibility compliance. Full manual keyboard, screen-reader, populated/error-state, zoom and real-device review remain required. Hosted CI and live E2E cannot be inferred from local test success.

Phase 1 local results on 2026-11-06: Python 3.13 pinned backend 122 passed; Node 22 frontend 65 passed and build succeeded; npm audit 0; five disposable care journeys; partial/empty doctor journey and 96 plus three automated axe/overflow scans passed. See the current audit for scope and caveats.

Phase 2: `npm run test:e2e:patient-management` exercises only an explicitly configured disposable synthetic database, creates a fictional profile, provisions one disposable account and records a follow-up completion. Never run it against production or valuable data. `npm run test:e2e:partial` covers partial/empty doctors. See the application audit for current results, prior failures and remaining verification.

Phase 3: `npm run test:e2e:login-throttle` intentionally locks the explicitly configured disposable synthetic account for the login window; never run against production or valuable accounts. Local backend 130 passed; frontend 71 passed and build/audit passed.

Phase 4: `npm run test:e2e:care-queue` requires an explicitly configured, pre-populated disposable synthetic queue of at least 51 items. It checks pagination, open states, filtering, selection and three automated axe/overflow scans; see the audit for execution results and limitations.

Phase 5: `npm run test:e2e:focused-queue` **mutates** a pre-populated local disposable synthetic fixture; it requires `E2E_DISPOSABLE=1`, a loopback `E2E_BASE`, credentials and Chromium. Record #1 for all five types must exist on the assigned patient and lie beyond the recent history caps; upload #1 must have a downloadable test PDF and follow-up #1 must be due and linked to check-in/upload #1. Never run it against valuable data. The script reviews and completes those records, checks exact IDs/context, keyboard focus and runs three axe/overflow scans. See the audit for execution results and remaining manual checks.

Phase 6: `npm run test:e2e:patient-history` requires a local disposable fixture with a doctor assigned to PG-0001, another doctor assigned elsewhere, a linked patient, 101 check-ins/uploads/reviews/plan versions and 501 diary/daily records (including shared and private reviews); provide `E2E_DISPOSABLE=1`, `E2E_BASE`, `E2E_DOCTOR`, `E2E_OTHER_DOCTOR`, `E2E_PATIENT`, `E2E_PASSWORD`, and `E2E_CHROMIUM_PATH`. It reads histories, downloads a synthetic PDF and signs in but does not write care records. It checks six histories, patient/doctor isolation, shared-review filtering and three automated axe/overflow scans. Never use valuable or production data.
