# Testing and QA

Run in a disposable synthetic environment: `python -m pytest backend/tests -q`, `npm --prefix frontend ci`, `npm --prefix frontend test`, `npm --prefix frontend run build`, and `npm --prefix frontend audit --audit-level=low`. CI uses Python 3.13 and Node 20. Browser harnesses in `frontend/e2e` require explicit disposable credentials; several write synthetic test records and must never target production. See [release readiness](FINAL_RELEASE_READINESS.md) and [application audit](COMPLETE_APPLICATION_AUDIT.md) for dated evidence and gaps.

Automated axe and responsive checks do not establish accessibility compliance. Full manual keyboard, screen-reader, populated/error-state, zoom and real-device review remain required. Hosted CI and live E2E cannot be inferred from local test success.

Phase 1 local results on 2026-11-06: Python 3.13 pinned backend 122 passed; Node 22 frontend 65 passed and build succeeded; npm audit 0; five disposable care journeys; partial/empty doctor journey and 96 plus three automated axe/overflow scans passed. See the current audit for scope and caveats.
