# v6 acceptance evidence

Performed 2026-11-07 in the build sandbox against the real code and, for extraction checks, against the shipped ZIP itself.

## Working-tree test matrix (v6 complete build)

| Suite | Result |
|---|---|
| Backend `pytest backend/tests/` | **151 passed** (141 v5 + 10 new v6 tests in `test_v6_risk_insights.py`) |
| Frontend `npx tsc --noEmit` | clean |
| Frontend `npm test` (vitest) | **78 passed** (73 v5 + 5 new in `workspace/V6.test.tsx`) |
| Frontend `npm run build` | OK (vite, chunks rebuilt) |
| Browser (real Chromium) | `browser_verify_workspace`: **15/15 PASS** · `browser_verify_doctor_patient`: **14/14 PASS** · `browser_verify_v6`: **7/7 PASS** (`V6_BROWSER_RESULTS.json`, screenshots in `screenshots/`) |

## Clean-extraction verification (ZIP unpacked to a fresh directory)

- `python -m venv` + `pip install -r requirements.txt` → OK.
- Backend suite: **151 passed**, run per-module in this RAM-constrained sandbox (single-process totals in the working tree are listed above; modules `41/46/14/18/9/13/10 passed` = 151).
- Frontend: `npm ci` → OK; `tsc --noEmit` clean; `npm test` **78/78**; `npm run build` OK.
- `uvicorn backend.app.main:app` boots on disposable DB; verified live: `/api/health` ok, doctor login, `/api/workspace/risk-overview` (120 rows), `/api/workspace/patients/PG-0071/risk` (24/48/72 horizons), patient insights 200, and patient → doctor prediction endpoint **403**.

## Honest statements

- No fabricated values, predictions, or test results anywhere in this report or the app.
- `browser_verify_*` suites used a disposable database copy (`PRANAGUARD_DB`), so the shipped DB keeps frozen contents.
- The replay dataset window (currently 2026-07-27 → 2026-09-13 UTC) predates live daily-record dates; charts show honest empty states naming that window rather than filling gaps.
