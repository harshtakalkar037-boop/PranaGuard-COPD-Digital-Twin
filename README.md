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
| Care workspace | ✅ signed-in workspace, unified directory, multi-step onboarding, Care Action Centre with persisted review workflow, patient 360° profile (overview/sputum/care plan/activity/reviews), doctor-scoped API authorization, honest error taxonomy, grouped navigation |
| **Doctor + Patient dashboards** | **✅ connected pair on one assigned synthetic record: patient daily wellbeing log + sputum diary + medication adherence (audited corrections), doctor-reviewed flags, clinical document upload/share with SHA-256 provenance, follow-up instructions, patient home summary, uniform audit trail; exactly 3 new patient nav items** |
| **v6: doctor risk visibility + patient health insights (this build)** | **✅ additive: 24/48/72h risk cards (timestamp, model version, freshness, completeness, review status) on doctor dashboard watchlist, patient profile *Model risk* tab and care-review context; timestamped prediction-history trend (`005_prediction_history` — additive migration, no duplicates, versions identified, raw scores never modified); engine reuse for explanations. Patient side: home summary lines, log-completion/adherence/review-status counts, insights tab with interactive graphs (symptom/breathlessness/cough, replay breathing-rate, sleep, activity, hydration, adherence, wellbeing) with 7/30/90-day + custom range filters and honest empty states. Patients are hard-blocked (403) from every doctor-only prediction endpoint. All outputs labelled "Experimental synthetic-data model estimate. Not clinically validated. Not intended for diagnosis, triage, or treatment decisions."** |

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
  care plans+revisions, review workflow+timeline, notification reads; `004` doctor+patient records,
  follow-ups, documents, medication adherence log; `005` prediction history: append-only timestamped captures of
  frozen-model outputs, unique per (patient, horizon, model version, state version)). Applied automatically on boot;
  original tables are never erased or rewritten. Failed migrations roll back.
- `PRANAGUARD_DB=/path/to/copy.sqlite` points the API at a disposable database copy for experiments.

## Testing

```bash
# Backend: 132 tests (original + enhanced + workspace auth/scoping/isolation)
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

Latest verification evidence: `docs/doctor-patient-verification/BROWSER_DOCTOR_PATIENT.json` (14 round-trip
checks across the doctor and patient dashboards), `docs/workspace-verification/BROWSER_WORKSPACE.json`
(15 workspace checks) and `docs/model48-v3/BROWSER_MODEL48_V3_COMPLETED.json` — real-Chromium evidence
against the shipped code. Backend suite: **141 passed**; frontend suite: **73 passed**.

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
                                    sputum, care plans, review queue/workflow (state machine + timeline)
  migrations/                       001–003 additive, checksummed
models_store/, baseline_outcomes/   frozen trained artifacts; findings/ hold-out finalist registry
experiments-v2…v4, docs/model*v*/   versioned studies (v3 active experimental; v2/v4 rejected, preserved)
frontend/src/
  App.tsx + pages/, components.tsx, styles.css   original experience (hash-protected)
  pages-enhanced/, Enhanced*.tsx                 v2/v3/v5/model-science pages
  workspace/                        NEW: Login, Directory+Onboarding tabs, Profile tabs, CareCentre, Workspace.css
docs/                               UPGRADE_PLAN, IMPLEMENTATION_SUMMARY, DOCTOR_PATIENT_* (plan + delivery), verification evidence
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
- No external email/push delivery is shipped; notification centre is in-app with opt-in local primitives.

## Provenance

Fork lineage and team context: see `README-original-backup.md` (verbatim original) and
`docs/enhanced/TEAM_INFO.md`. Frozen-cohort digests: `docs/enhanced/BASELINE_MANIFEST.json`.
Study evidence: `docs/final-submission/CHAMPION_SELECTION.md`, `docs/model48v3/`, `docs/enhanced/results/`.

### Doctor ↔ patient demo workflow (this build)

1. Sign in as `dr-atlas` → **Patients** → open `PG-0071` → tabs *Daily wellbeing* and *Documents & follow-ups*.
2. Sign out, then sign in as `pat-pg0071` → the patient shell opens with **three** items only:
   Patient Home, My Health Records, Clinical Documents. Patient submissions appear in the doctor's view
   and doctor-shared plans/follow-ups/documents appear in the patient's view (same SQLite record).
3. Details: `docs/DOCTOR_PATIENT_DELIVERY.md`.

### v6 flows (doctor risk visibility + patient insights)

1. Sign in as `dr-atlas` → **Care action centre** shows the experimental 72h risk watchlist (raw replay-model scores, sorted, with review status; disclaimer inline).
2. **Patients** → open `PG-0071` → **Model risk** tab: 24/48/72h cards with prediction timestamp / `pg-synthetic-v1` version / data completeness / review status; timestamped prediction-history chart; on-demand 72h feature-contribution table (reuse of the frozen `engine.explain`).
3. In an open **care review** the same read-only risk cards appear as context — documentation only, never auto-driving treatment.
4. Sign in as `pat-pg0071` → **Patient Home** shows data-backed summary lines (log completion, adherence counts, doctor review status); **My Health Records → Insights** renders interactive graphs with 7/30/90-day + custom date filters, units, tooltips, and honest empty states. The frozen replay window (currently 12–13 Sep 2026 UTC) is surfaced so gaps are never silently filled.
5. Patients calling any doctor-only prediction endpoint receive **403** (see `backend/tests/test_v6_risk_insights.py`).
6. Full evidence: `docs/ENHANCEMENT_IMPLEMENTATION_REPORT.md`, `docs/v6-verification/`.

> PranaGuard · Synthetic proof of concept · pg-synthetic-v1 · no clinical validation
