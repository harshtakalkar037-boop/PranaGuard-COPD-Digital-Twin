# PranaGuard — unified COPD digital-twin workspace (advanced submission build)

PranaGuard is a **synthetic, research-only proof of concept** for post-discharge COPD monitoring:
patient risk dashboards, replayable digital twins from frozen multiseed models, versioned model-ranking
evidence with rollups and ablations, and a **complete clinician care workspace** — one signed-in experience
with a unified patient directory, sputum diaries, care-plan documentation and a persisted Care Action Centre.

**Do not use this project for clinical decisions.** Everything ships with synthetic data only; the frozen
baseline cohort is read-only research data (120 synthetic patients / 3,000 window states), and live
environmental data is never model input.

---

## What's in this build

| Layer | Status |
|---|---|
| Original hackathon dashboard (baseline, twins, signals, alerts, export) | ✅ preserved — 26/26 original files hash-verified unchanged |
| Enhanced submission work (registry read-only, notifications, device/environment surfaces, email-engine primitives, hash-guarded provenance, model-ranking study infrastructure) | ✅ preserved and working |
| Experiment v2 (6-hour personalized) | ❌ rejected — evidence kept, inactive, honestly labelled |
| Experiment v3 (48-hour early-warning `pg48-v3-multiseed`) | ✅ active experimental model — PASSED frozen gate |
| Post-v3 analysis artifacts (v4 evidence, gap analysis, final selection report, TreeSHAP cache) | integrity-verified at startup |
| v5 study explorer (unified results browser: history, gates, rollups, ablations, top-5, leaderboard, scatter, comparison, frozen-vs-active) | ✅ additive, on top of frozen studies |
| **Product upgrade (this build)** | **✅ signed-in workspace, unified directory, multi-step onboarding, Care Action Centre with persisted review workflow, patient 360° profile (overview/sputum/care plan/activity/reviews), doctor-scoped API authorization, honest error taxonomy, grouped navigation, responsive + accessible UI** |

## Quick start (linear, ~5 minutes)

Prerequisites: **Python ≥3.11** and **Node ≥20 / npm**. Copy `.env.example` → `.env` (safe defaults
already match; secrets are never required for local demo).

```bash
cd PranaGuard-Platform
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
npm --prefix frontend install
```

Terminal 1 — API (serves on **:8000**, also serves `/docs`):

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — Dashboard (**:5173**, proxies `/api` → :8000):

```bash
npm --prefix frontend run dev
```

Open http://localhost:5173 and sign in with a **documented demo identity** (synthetic accounts, seeded on
first boot; passwords configurable via `PRANAGUARD_DEMO_*` env vars on first boot):

| Username | Password | Panel |
|---|---|---|
| `dr-atlas` | `prana-atlas-demo` | Doctor — full 120-twin synthetic panel |
| `dr-nova` | `prana-nova-demo` | Doctor — empty panel (auth/isolation demo) |
| `pat-pg0071` | `prana-patient-demo` | Patient — own synthetic record only |

Sessions are bearer tokens (PBKDF2-hashed demo passwords, 12-hour expiry, persisted in SQLite).

## Database & migrations

- SQLite WAL at `data/pranaguard.sqlite`, shipped with the frozen cohort (120 patients / 3,000 states;
  content digests verified at startup; `PRANAGUARD_STRICT_DATA=1` turns tampering into a fatal error).
- Additive, checksummed migrations in `backend/app/migrations/` (`001` enhanced monitoring,
  `002` environment backoff, `003` care workspace: users/sessions, assignments, sputum entries+attachments,
  care plans+revisions, review workflow+timeline, notification reads; `004` persistent demo login throttling; `005` immutable follow-up completion ledger). Applied automatically on boot;
  original tables are never erased or rewritten. Failed migrations roll back.
- `PRANAGUARD_DB=/path/to/copy.sqlite` points the API at a disposable database copy for experiments.

## Testing

```bash
# Backend: 139 tests (original + enhanced + workspace auth/scoping/isolation + follow-up ledger + alert/WebSocket scope)
.venv/bin/python -m pytest backend/tests/ -q

# Frontend: 63 tests across 5 suites (auth gate, directory, profile, care centre, errors, research pages)
npm --prefix frontend test

# TypeScript + production build
npm --prefix frontend run build

# Real-browser regression (Playwright + Chromium; disposable DB copy recommended):
PRANAGUARD_DB=/tmp/pg.sqlite .venv/bin/python -m uvicorn backend.app.main:app --port 8011 &
API_PROXY_TARGET=http://127.0.0.1:8011 npm --prefix frontend run dev &
.venv/bin/python -m scripts.browser_verify_workspace
.venv/bin/python -m scripts.browser_verify_model48_v3   # research-experience browser suite
.venv/bin/python -m scripts.verify_live_environment     # opt-in live provider check (PRANAGUARD_LIVE_ENV_ENABLED=true)
```

The unified integration branch currently passes 138 local backend tests and Python compilation. Vercel preview production build is READY; a separate Render preview service is LIVE with workspace authorization enabled. Frontend unit tests and a hosted authenticated browser journey are still pending; do not treat preview availability as production sign-off. The local browser evidence from the earlier build is not a fresh verification of this integration.\n\nLatest verification evidence: `docs/workspace-verification/BROWSER_WORKSPACE.json` (+`screenshots/`) and
`docs/model48-v3/BROWSER_MODEL48_V3_COMPLETED.json` — 15+18 real-Chromium checks against the shipped code.

## Production build & deployment

`npm --prefix frontend run build` → `frontend/dist/` static assets. Serve them behind any static host and
proxy `/api`, `/docs`, `/openapi.json` to the FastAPI process (`vite preview` works locally). No Docker or
external services are required; the only network dependency is the **opt-in** Open-Meteo free endpoints for
live environment panels (disabled by default — see below).

## Configuration (`.env`, backend only)

| Variable | Default | Purpose |
|---|---|---|
| `PRANAGUARD_DB` | `data/pranaguard.sqlite` | Database path (use a copy for risky testing) |
| `PRANAGUARD_DEMO_{ATLAS,NOVA,PATIENT}_PASSWORD` | documented demo values | Demo account passwords on first seed |
| `PRANAGUARD_TWIN_CACHE_PATH` | `models_store/artifacts/twin/twin_cache.sqlite` | Precomputed twin cache (hash-protected) |
| `PRANAGUARD_WATCHDOG_ENABLED` | `0` | Auto-recompute twins (never in demo mode) |
| `PRANAGUARD_LIVE_ENV_ENABLED` | `false` | Opt-in Open-Meteo live air/weather panels |
| `PRANAGUARD_EMAIL_*`, `PRANAGUARD_WEB_PUSH_PUBLIC_KEY` | unset | Optional notification delivery experiments (local SMTP only; no external email account is shipped) |

## Architecture map

```
backend/app/
  main.py, engine.py, store.py      frozen research API (patients/risk/history/explain/scenario/alerts/export…)
  enhanced/                         registry CRUD, preferences, alerts, devices, environment, evidence, email
  workspace/                        NEW: auth+sessions, doctor-scoped directory/overview/profile,
                                    sputum, care plans, review queue/workflow (state machine + timeline + follow-up completion ledger)
  migrations/                       001–005 additive, checksummed (login throttle + follow-up ledger)
models_store/, baseline_outcomes/   frozen trained artifacts; findings/ hold-out finalist registry
experiments-v2…v4, docs/model*v*/   versioned studies (v3 active experimental; v2/v4 rejected, preserved)
frontend/src/
  App.tsx + pages/, components.tsx, styles.css   original experience (hash-protected)
  pages-enhanced/, Enhanced*.tsx                 v2/v3/v5/model-science pages
  workspace/                        NEW: Login, Directory+Onboarding tabs, Profile tabs, CareCentre, Workspace.css
docs/                               UPGRADE_PLAN, IMPLEMENTATION_SUMMARY, verification evidence
```

## Honest limitations (unchanged commitments)

- **Synthetic only** — every patient, vitals source, diary entry and identity is fictional demo data.
- Research cohort is frozen/read-only; demo write flows touch only workspace tables, never frozen science.
- Baseline head model performance is below chance on the frozen synthetic test cohort (documented in the UI);
  the 48-hour v3 model is an experimental, synthetic-only improvement with its own honest evidence page.
- Live air/weather context is modelled gridded data (Open-Meteo CAMS), optional, informed-consent-free,
  and **never** an ML input; **USAQI ≠ CPCB/Indian NAQI**. IMD/CPCB feeds are explicitly labelled as
  *not integrated* where referenced.
- Device integrations are simulators/sandbox surfaces — presented as such, never as real telemonitoring.
- ARIMA/LightGBM/CatBoost baselines are honest underground benchmarks; the shipped runtime remains sklearn
  losses; what-if scenarios are noncausal ranked persistence checks.
- No external email/push delivery is shipped; notification centre is in-app with opt-in local primitives.\n- Demo username throttling is not distributed/IP-based anti-abuse protection; independent security review and manual accessibility review remain required.\n- Render preview uses free-tier ephemeral SQLite storage; records may reset on restart/redeploy. No production patient data or durable clinical records belong here. Persistent production storage, backup/restore and authenticated hosted E2E verification are not yet signed off.\n- Unified API enforcement is enabled only on the isolated preview service (`PRANAGUARD_REQUIRE_WORKSPACE_AUTH=1`); the production service has not been changed.

## Provenance

Fork lineage and team context: see `README-original-backup.md` (verbatim original) and
`docs/enhanced/TEAM_INFO.md`. Frozen-cohort digests: `docs/enhanced/BASELINE_MANIFEST.json`.
Study evidence: `docs/final-submission/CHAMPION_SELECTION.md`, `docs/model48v3/`, `docs/enhanced/results/`.

> PranaGuard · Synthetic proof of concept · pg-synthetic-v1 · no clinical validation
