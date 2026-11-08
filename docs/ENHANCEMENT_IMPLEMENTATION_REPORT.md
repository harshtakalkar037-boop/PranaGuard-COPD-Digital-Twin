# PranaGuard v6 — Enhancement Implementation Report

Date: 2026-11-07 · Build: `PranaGuard-v6-Complete-Enhanced-Platform` · Base: v5 delivery (`PranaGuard-Enhanced-v5-DoctorPatient.zip`, sha256 `a2cec3a2…bb7`)

## 1. Scope executed

Additive changes only; 100% of v5 behaviour preserved (see §6 tests).

**Doctor risk visibility (new)**
- 24/48/72 h risk cards showing the raw frozen replay-model score, prediction timestamp, model version (`pg-synthetic-v1`), input window, data completeness/imputation note, freshness (latest patient-record edit), latest care-review status, and calibration note ("none — raw LightGBM score").
  - Doctor dashboard: **72-hour model risk watchlist** (Care action centre), sorted by 72h risk, cohort-origin aware.
  - Patient profile: new **Model risk** tab.
  - Care review workspace: read-only risk context panel embedded under the open review.
- **Prediction history (trend):** timestamped captures of raw model outputs in a new append-only table `prediction_history` (migration `005`), unique per `(patient_id, horizon, model_version, state_version)` — duplicates are never re-recorded, model versions always identified, raw scores never modified. Rendered as a 3-horizon line chart.
- **Risk explanation:** reuses the existing frozen `engine.explain` (TreeSHAP raw contributions, top 12 drivers with labels/values); no new model science invented.

**Patient health insights (new)**
- Patient Home adds data-backed **Recent health summary** lines (log-completion over 14 days, adherence n/m over 14 days, latest doctor review line). Navigation stays exactly 3 items.
- My Health Records adds an **Insights** tab: breathlessness & cough (from sputum diary), symptom-score trend (frozen replay), breathing-rate history (frozen replay, daily min/mean/max), sleep, activity, hydration, medication adherence, wellbeing check-ins — with 7/30/90-day presets + custom date range, units in subtitles, tooltips, and honest empty states that name the replay coverage window instead of fabricating data. Missing dates remain missing in all series.

**Labelling (everywhere):** "Experimental synthetic-data model estimate. Not clinically validated. Not intended for diagnosis, triage, or treatment decisions." Frozen-replay vitals labelled "not wearable telemetry". Risk never auto-drives treatment.

## 2. Files added/modified (v6 delta)

| File | Status |
|---|---|
| `backend/app/migrations/005_prediction_history.sql` | new — additive, idempotent append-only table + index |
| `backend/app/workspace/service.py` | modified — `risk_snapshot`, `risk_history`, `risk_overview`, `risk_explanation`, `patient_insights`, `patient_home_summary_lines`; `patient_home` extended with `summary_lines` |
| `backend/app/workspace/routes.py` | modified — 6 GET routes: `/patient/insights`, `/risk-overview`, `/patients/{pid}/risk{,/history,/explanation}` |
| `backend/tests/test_v6_risk_insights.py` | new — 10 tests (RBAC 403s, no-duplicate history, migration shape, date validation, honest series) |
| `frontend/src/workspace/Risk.tsx` | new — doctor risk cards / history chart / explanation |
| `frontend/src/workspace/Insights.tsx` | new — patient insights tab with 8 charts + date filters |
| `frontend/src/workspace/{CareCentre,Profile,PatientHome,Records,types}.tsx/ts` | modified — wiring of the above |
| `frontend/src/workspace/V6.test.tsx` | new — 5 component tests with fixtures |
| `scripts/browser_verify_v6.py` | new — 7-step real-Chromium verification + screenshots (`docs/v6-verification/`) |
| `README.md`, this report, `docs/ZIP_DELIVERY_VERIFICATION.md` | modified/new docs |

No dependency additions. Frozen ML pipeline, artifacts, splits and the 120-patient/3,000-state cohort untouched (startup digest guard unchanged).

## 3. Authorization matrix (unchanged rules, newly exercised)

| Resource | Doctor | Patient |
|---|---|---|
| `/workspace/risk-overview`, `/patients/{pid}/risk*` | assigned doctor only (404/403 otherwise) | **403** on all, tested |
| `/workspace/patient/insights` | 403 | own record only |
| care plans | doctor write | read-only (unchanged) |

## 4. Bottom-line caveats (unchanged)

72h baseline model remains below chance / zero sensitivity; these v6 surfaces display that frozen output honestly, with the disclaimer inline, and never gate any treatment workflow. No fabricated predictions, values or test results anywhere.
