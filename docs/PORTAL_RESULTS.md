# Initial portal upgrade verification (historical)

These results describe the earlier portal upgrade, not the final connected-care implementation. For current results and known limitations see [COMPLETION_REPORT.md](COMPLETION_REPORT.md).

- Backend: `pytest backend/tests -q` — 92 passed, including five portal tests and existing synthetic dashboard tests explicitly run in legacy demo mode. One upstream Starlette TestClient deprecation warning.
- Frontend: `npm test` — 38 passed across three test files; `npm run build` passed.
- Local Vite proxy smoke checks: `/` and `/api/health` returned 200; unauthenticated `/api/overview` returned 403; unauthenticated `/api/portal/me` returned 401.
- `npm audit --omit=dev` reported zero production vulnerabilities. `npm ci` reported four vulnerabilities in the full dependency tree (two moderate, two critical); review development dependencies before deployment.
- This sandbox only had Python 3.11; the existing pinned NumPy requires Python 3.12. Tests ran in an isolated venv with compatible resolved versions rather than the exact Python 3.12 lock, including FastAPI 0.162.0, NumPy 2.4.6, pandas 3.1.1, LightGBM 4.7.0, scikit-learn 1.9.1 and python-multipart 0.0.33. Exact pinned-environment verification remains necessary.
- The new portal tests are HTTP and component tests, not full browser end-to-end, security penetration, accessibility or clinical validation tests.

## Files

New: `backend/app/migrations/003_portals.sql`, `backend/app/portal.py`, `backend/app/portal_admin.py`, `backend/tests/test_portal.py`, `docs/PORTAL_PLAN.md`, `docs/PORTALS.md`, `docs/PORTAL_RESULTS.md`, `frontend/src/Portal.tsx`, `frontend/src/Portal.test.tsx`, `frontend/src/portal.css`.

Modified: `.gitignore`, `README.md`, `backend/app/main.py`, `backend/tests/conftest.py`, `backend/tests/test_enhanced.py`, `frontend/src/App.test.tsx`, `frontend/src/main.tsx`, `requirements.txt`, `requirements-lock.txt`. Existing test fixtures explicitly select legacy mode and the migration count includes the new migration; the existing frontend test mock now supplies the enhanced environment/registry responses consumed by the dashboard.

Models, data-generation, model training, scientific artifacts, existing migrations and synthetic datasets were not modified. Portal-specific limitations and the unsafe legacy isolation boundary are documented in `PORTALS.md`.
