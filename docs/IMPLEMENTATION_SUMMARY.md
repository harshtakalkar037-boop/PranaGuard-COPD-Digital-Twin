# Implementation summary — product upgrade (care workspace build)

Date: 2026-11-07 · Base: `PranaGuard-Enhanced-v3.zip` (SHA-256 `cb73e1…835b`) · All work performed in a
local isolated copy (`PranaGuard-Platform/`); the original frozen repository was never modified.

This document is the audit trail for the upgrade: what was planned, what was built, exactly which files
changed, how it was verified, and what remains honestly out of scope.

---

## 1. Scope executed (against the 18-section spec)

| # | Spec area | Result |
|---|---|---|
| 1 | Audit existing app | 26/26 original protected files SHA-verified unchanged before signing off; SQLite cohort digests (120 patients / 3,000 states) verified intact |
| 2 | Information architecture | Sidebar regrouped into **4 meaning groups** (Workspace / Twin & research / Care records / Data & system) using existing theme; no new design system, fonts or gradients |
| 3 | Canonical patient directory | `/api/workspace/patients` — server-side search, city/origin/risk filters, sort (name/city/risk/updated), pagination, doctor-scoped, prediction-availability badge |
| 4 | Add-patient onboarding | Existing multi-step enhanced registration retained as the "Onboarding" tab (validation, fictional-identity confirmation, dedupe via request id, persisted, confirmed) |
| 5 | Frozen cohort protection | No write path to the 120-patient research cohort; demo writes only to workspace tables; digests re-verified post-build |
| 6 | Care Action Centre | Real persisted workflow: summary metrics from SQLite, review queue (search/status filter/pagination), new-review panel, review workspace with **state machine** (`new → awaiting_review → under_review → follow_up_scheduled → completed → closed`, illegal transitions 409), timeline events, deep patient + research context |
| 7 | Sputum diary | Structured entries (colour/volume/consistency/cough/breathlessness/note), optional photo evidence (base64 ≤512 KB, SHA-256 stored, rendered from local file only), pagination, per-patient history |
| 8 | Care plans | Documented goals/actions/review-cadence editor with **append-only revisions** (every save versioned; history visible) |
| 9 | Notification centre | Existing module retained; badge in topbar; linked into profile "Reviews & notifications" tab |
| 10 | Environment provenance | Existing modelled-context module retained, labelled (modelled external, USAQI ≠ CPCB NAQI) |
| 11 | Research tools | Digital twins, explainability, what-if studio, validation/study pages preserved untouched |
| 12 | Functionality/no fakes | Every control wired to a real endpoint; unavailable features labelled honestly (e.g. model activation for uncalibrated patients returns a labelled 404, not a silent fake) |
| 13 | Errors | `ApiError{status}` + `explainError`: network failure / 401 / 403 / 404 / 409 / 422 / 500 mapped to distinct, actionable messages — no blanket "Backend unavailable" |
| 14 | Auth & authorization | Seeded demo users (PBKDF2-SHA256, 120k iterations, 12 h bearer sessions), doctor role scoped to assigned patients, patient role to own record; **two-doctor isolation** proven in tests and browser |
| 15 | `/api/overview` scoping | `TwinEngine.cohort(patient_ids=...)` restricts every aggregate (patients, trend SQL, alerts) with empty-set handling and zero cross-scope leakage; workspace `/overview` is always scoped |
| 16 | Responsive & accessibility | 390 px viewport: no horizontal overflow (browser-verified); labels on all controls, icon+text status (no colour-only), keyboard-focusable tabs; original responsive behaviour kept |
| 17 | Migrations/data safety | `003_care_workspace.sql` is additive-only (users, sessions, assignments, sputum+attachments, plans+revisions, reviews+timeline, notification reads), checksummed, transactional, applied automatically; no secrets in ZIP |
| 18 | Testing | Backend **132/132**, frontend **63/63** (5 suites incl. new 13-test workspace suite), `tsc -b` clean, production build clean, **15/15 real-Chromium checks** incl. persistence-across-reload, mobile and console-error assertions |

## 2. Files created

```
backend/app/workspace/__init__.py
backend/app/workspace/service.py            auth, scoping, directory, profile aggregate, sputum, plans, reviews
backend/app/workspace/routes.py             /api/workspace/* router (login/logout/me/overview/patients/…)
backend/app/migrations/003_care_workspace.sql
backend/tests/test_workspace.py             13 tests (auth, isolation, directory, reviews 409, plans, sputum)
frontend/src/workspace/types.ts
frontend/src/workspace/Login.tsx            quick-pick demo identities + form, honest demo framing
frontend/src/workspace/Directory.tsx        directory + PatientsSection (Directory | Onboarding tabs)
frontend/src/workspace/Profile.tsx          banner + Overview/Sputum/Care plan/Activity/Reviews tabs
frontend/src/workspace/CareCentre.tsx       metrics, queue, NewReview, ReviewWorkspace + timeline
frontend/src/workspace/workspace.css        new classes only, existing palette (#103b34/#f6f8f7/#1b6b55/#2b9a82)
frontend/src/workspace/Workspace.test.tsx   13 tests
frontend/src/workspace/__fixtures__/*.json  10 real API responses captured from a live TestClient
docs/UPGRADE_PLAN.md                        pre-implementation audit + plan
docs/workspace-verification/BROWSER_WORKSPACE.json + screenshots/ (2 PNGs)
scripts/browser_verify_workspace.py         Playwright harness (auth-aware)
```

## 3. Files modified (all additive/behaviour-preserving)

| File | Change |
|---|---|
| `backend/app/engine.py` | `cohort()` gained optional `patient_ids` scoping (24 lines changed; default path byte-identical behaviour) |
| `backend/app/main.py` | +4 lines: import + instantiate `Workspace`, mount router |
| `backend/tests/test_enhanced.py` | migration-count assertion now derives from `migrations/*.sql` glob instead of hard-coded 2 (keeps guard meaningful as migrations grow) |
| `frontend/src/api.ts` | `ApiError` carries HTTP status; `explainError` taxonomy; Authorization header support |
| `frontend/src/types.ts` | `View` union extended with `care` and `profile` |
| `frontend/src/App.tsx` | session bootstrap gate → LoginScreen; grouped sidebar; user chip + sign-out; mounts PatientsSection/CareCentrePage/ProfilePage; replay toolbar & export hidden on care/profile views |
| `frontend/src/App.test.tsx` | test harness seeds demo session token + `/workspace/me` fixture route (existing 50 assertions unchanged in intent) |
| `README.md` | full rewrite: quick start, demo credentials, DB/migrations, tests, deploy, env vars, architecture map, honest limitations |

No deletions. `frontend/src/styles.css` and `frontend/src/components.tsx` are untouched (hash-protected).

## 4. Security & authorization decisions

- Demo authentication exists **only** to exercise scoping — passwords are documented demo values,
  overridable via `PRANAGUARD_DEMO_*` env vars on first seed; no real credentials exist anywhere.
- Bearer tokens are stored **hashed**; raw tokens never appear in logs, API responses or the archive.
  OpenAPI spec contains no `token_hash`.
- Doctor assignment is resolved server-side on every workspace request; a doctor cannot read another
  doctor's patients, reviews, plans, diaries or notifications (403 verified in tests + browser).
- Original research API remains unauthenticated (demo posture, documented); the workspace layer adds
  auth without weakening anything that existed. No unauthenticated admin endpoint was introduced.
- Sputum photos are validated (type/size ≤512 KB), stored as local files with SHA-256 provenance,
  served from this origin only.

## 5. Verification evidence (reproducible)

| Suite | Command | Result |
|---|---|---|
| Backend | `.venv/bin/python -m pytest backend/tests/` | **132 passed** |
| Frontend | `npm --prefix frontend test` | **63 passed (5 files)** |
| Types/build | `npm --prefix frontend run build` | clean |
| Browser | `scripts/browser_verify_workspace.py` (Chromium, disposable DB) | **15/15 PASS** — `docs/workspace-verification/BROWSER_WORKSPACE.json` |
| Frozen baseline | digest re-check vs `docs/enhanced/BASELINE_MANIFEST.json` | 26/26 files + DB rows unchanged |

Browser suite covers: login (valid + rejected bad password), grouped nav, original theme colour,
directory search/pagination, profile tabs, care-plan save with feedback, sputum save + immediate render,
care metrics, review create → reload persistence, **two-doctor isolation in the browser**, session
persistence across reload, sign-out, research workspace preserved, 390 px no-overflow, and
zero console/JS errors or external requests.

## 6. Known limitations (carried, not hidden)

- Synthetic data only; no clinical validation; frozen-cohort limitations labels retained everywhere.
- Newly registered demo patients have no ML prediction (72 h baseline rule) — shown as "unavailable",
  never faked.
- The review workflow has no multi-user concurrency beyond state-version conflict checks (409);
  notification delivery remains in-app (email/web-push remain opt-in local primitives).
- Authentication is demo-grade by design (local demo accounts); production IdP/OIDC is out of scope
  for this synthetic proof of concept and is documented as such.

## 7. Rollback

Every capability above is additive. Rolling back = removing the router mount in `backend/app/main.py`
(4 lines) — the workspace tables are ignored by the original codebase, and migration 003 is inert to it.
The v3 behaviour without the workspace can be reproduced exactly from `PranaGuard-Enhanced-v3.zip`.
