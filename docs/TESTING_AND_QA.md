# Testing and QA

Run in a disposable synthetic environment: `python -m pytest backend/tests -q`, `npm --prefix frontend ci`, `npm --prefix frontend test`, `npm --prefix frontend run build`, and `npm --prefix frontend audit --audit-level=low`. CI uses Python 3.13 and Node 20. Browser harnesses in `frontend/e2e` require explicit disposable credentials; several write synthetic test records and must never target production. See [release readiness](FINAL_RELEASE_READINESS.md) and [application audit](COMPLETE_APPLICATION_AUDIT.md) for dated evidence and gaps.

Automated axe and responsive checks do not establish accessibility compliance. Full manual keyboard, screen-reader, populated/error-state, zoom and real-device review remain required. Hosted CI and live E2E cannot be inferred from local test success.

Phase 1 local results on 2026-11-06: Python 3.13 pinned backend 122 passed; Node 22 frontend 65 passed and build succeeded; npm audit 0; five disposable care journeys; partial/empty doctor journey and 96 plus three automated axe/overflow scans passed. See the current audit for scope and caveats.

Phase 2: `npm run test:e2e:patient-management` exercises only an explicitly configured disposable synthetic database, creates a fictional profile, provisions one disposable account and records a follow-up completion. Never run it against production or valuable data. `npm run test:e2e:partial` covers partial/empty doctors. See the application audit for current results, prior failures and remaining verification.

Phase 3: `npm run test:e2e:login-throttle` intentionally locks the explicitly configured disposable synthetic account for the login window; never run against production or valuable accounts. Local backend 130 passed; frontend 71 passed and build/audit passed.
