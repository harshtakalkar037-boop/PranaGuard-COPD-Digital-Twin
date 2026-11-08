# V7 Verification Report — Final Enhanced Platform

Date: 2026-11-08. Base: v6 platform (all features preserved) + v7 external research models (additive). Every check below was executed in this workspace; anything not executed is not claimed.

## 1. Preserved platform (regression surface)

- Backend suites, run per file: `test_api.py` 41, `test_enhanced.py` 46, `test_model48.py` 14, `test_model48_v3.py` 18, `test_patient_records.py` 9, `test_v6_risk_insights.py` 10, `test_workspace.py` 13 — **151 passed, 0 failed**.
- Frontend suite: `App.test.tsx`, `Enhanced.test.tsx`, `Model48V3.test.tsx`, `Study.test.tsx`, `V6.test.tsx`, `Workspace.test.tsx`, `PatientDash.test.tsx` — **78 tests passed** with the new module (86 total incl. research).
- `tsc -b` clean; `vite build` succeeds.
- Frozen DB byte-identical to v6 delivery: `data/pranaguard.sqlite` sha256 `9859ea123df5c591426c7b6dae23c52bdab2e0b6a446fb075ff5586756fdbc28`; boot applies migrations [1,2,3,4,5,6] with migration-hash checks.
- Home screen unchanged except the muted eyebrow line; no new banners, no renaming, no redesign.

## 2. New research surface (executed)

- `backend/tests/test_research_models.py` — **12 passed**: registry contains exactly the two external models with complete fields; production twin absent from the registry; cough metrics pinned (AUROC 0.9316, AUPRC 0.8293 vs prevalence 0.262, sensitivity 0.578 disclosed, train+test = 853); inference returns calibrated probabilities from the real artifact and persists to `model_predictions`; garbage/short audio gets a 4xx/503, never an invented label; attribution contains no SHAP; TOLIFE reconciled audit (80/42/0, 42 in-frame, 32 prior-7d, 30 evaluable) and 24/48/72h AUROCs 0.355/0.389/0.393 with honest CIs; participants strictly `tolife:` coded; `pg-synthetic` twin untouched (`/api/health`, 120-patient overview).
- Frontend `src/research/Research.test.tsx` — **8 passed** (cards, registry expansion, low-sensitivity disclosure, inference gating incl. explicit unavailability state, multipart upload path, TOLIFE audit numbers, channel switching).
- Live smoke over `TestClient`: all 8 research endpoints 200; cough WAV inference 200 with persisted audit row; migration `006` applied and seeded (853 cough index rows, 80 events, 86 participants, 2 experiment runs).
- No combined leaderboard anywhere: UI notice + per-model endpoints only (frontend test asserts the non-merging notice).

## 3. Schema / migration check

`006_research_models.sql` uses only `CREATE TABLE IF NOT EXISTS` + additive foreign keys; existing tables and rows are not modified. Boot hash-ledger confirms migrations 1–6; no v6 SQL was edited.

## 4. Security

- Cough upload: multipart, 40 MB cap, non-audio → error; feature extraction runs backend-side; input hash sha256-16 persisted; no raw audio stored.
- Research endpoints are read-only except the inference audit insert; no route reaches into twin tables; authorization headers flow exactly as in v6 (`X-Demo-Token`, workspace bearer).
- No secrets in repo: grep-verified (no tokens/keys); `.env` is not shipped (`.env.example` is placeholder-only); datasets are not redistributed (see Download Instructions).

## 5. Responsive / UI

Research page uses the existing panel/grid system; cards collapse at 900 px CSS breakpoint; navigation works on the mobile slide-over; tested components render in jsdom with mocked charts.

## 6. Cross-model integrity

Six checks: (a) registry ids distinct from twin version; (b) no SHAP in cough attribution; (c) TOLIFE participants never share `PG-` ids; (d) evidence labels REAL_OBSERVED/REAL_DERIVED/SYNTHETIC_GENERATED preserved per surface; (e) metrics never co-displayed; (f) home screen prominence rule respected (no banner).

## 7. Clean-extraction verification

The final ZIP was re-extracted into an empty directory and re-verified with zero missing and zero mismatched files, migrations re-applied 1–6, 120 patients / 3000 states / 10 endpoints 200 (incl. research). See `PRANAGUARD_FINAL_ZIP_VERIFICATION.json`, delivered alongside the ZIP (it carries the zip sha256, file count and all executed checks).

## 8. Known limitations (unchanged policy)

Cough file-level independence unverifiable; TOLIFE probe weak by design disclosure; horizon analysis limited to 24/48/72h because those are the windows the corrected pipeline supports — nothing else was manufactured.
