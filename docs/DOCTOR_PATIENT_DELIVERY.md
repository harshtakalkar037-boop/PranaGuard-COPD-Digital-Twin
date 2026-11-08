# Delivery report — Doctor Dashboard + Patient Dashboard upgrade

Date: 2026-11-07 · Built on top of `PranaGuard-Enhanced-v4-Workspace.zip` (source of truth; extracted,
re-verified 132/132 backend + 63/63 frontend **before** any change). No original module was deleted,
rewritten or replaced. Frozen science, models, cohort, theme, and all pre-existing features remain intact.

## 1. What was added (all additive)

### Doctor dashboard (existing shell preserved; new capability inside existing sections)
- Existing patient profile (`Patients → Profile`) gained two tabs:
  - **Daily wellbeing** — the patient's hydration/nutrition/activity/sleep/wellbeing entries with
    doctor "Mark reviewed" (immutable) + medication adherence reports + doctor-authored demo
    medication list.
  - **Documents & follow-ups** — upload (title/type/date/notes + file), list with SHA-256 provenance,
    open/download, audited remove; follow-up instructions with due date, complete/cancel lifecycle.
- Audit trail endpoint `/api/workspace/patients/{pid}/audit` for the assigned doctor, listing every
  workflow action with actor, role, timestamp and before/after snapshots.

### Patient dashboard (new role-based shell — exactly the 3 permitted new sidebar items)
- **Patient Home** — today's log status, streak, follow-up reminders (overdue + upcoming), care-plan
  summary (read-only), reviewed status, recent records, document count.
- **My Health Records** — daily wellbeing log (hydration, food notes, activity minutes, sleep hours +
  quality, wellbeing, notes) with audited corrections; sputum diary self-entry incl. optional photo
  (existing ≤512 KB attachment rule); medication adherence against the clinician-documented list only
  (missed dose requires a reason); history & trends.
- **Clinical Documents** — patient read-only list + integrity-checked downloads of doctor-shared files.
- Patients sign in to this shell directly; they never see the clinician/research navigation.

### Connected-record guarantees (backend-enforced, not button-hiding)
- Patient token → own record only (`403` on any other patient id across every new endpoint).
- Doctor token → assigned patients only (`403` otherwise); unassigned doctor verified in tests + browser.
- Every important action (log create/edit, reviewed flags, medication add/report, document
  upload/delete, follow-up lifecycle, care-plan save, review create/update, sputum add/review) writes an
  `audit_events` row with timestamps and user attribution; patient edits preserve original content in the
  audit snapshot.

## 2. Database
Migration `004_patient_records.sql` (additive, transactional, idempotent): `daily_logs`,
`plan_medications`, `med_adherence`, `documents`, `follow_ups`, `audit_events`. No existing table/row
altered. Shipped SQLite stays at migrations 001–002 and upgrades on first boot like 003 does;
original cohort digests re-verified unchanged.

## 3. Demo configuration (synthetic only)
| Account | Password (demo only) | Link |
|---|---|---|
| `dr-atlas` | `prana-atlas-demo` | Doctor — one-to-one demo link with PG-0071 + full synthetic cohort view |
| `pat-pg0071` | `prana-patient-demo` | Patient — sees only own record |
| `dr-nova` | `prana-nova-demo` | Empty panel — used to prove isolation |

Seeded examples (idempotent, first-boot only): 3 daily logs, 2 adherence reports, 1 scheduled follow-up
(+3 days), 1 demo text document ("Demo COPD action plan summary (fictional)"), 1 documented demo
medication. **Demo credentials are for local demonstration only — never production credentials.**

## 4. Test results actually executed (this session)

| Suite | Command | Result |
|---|---|---|
| Backend (all) | `pytest backend/tests/` | **141 passed / 141** — 11 new patient-record tests (+ existing 130) |
| Frontend (all) | `npm test` (vitest) | **73 passed / 73** — 10 new patient-dashboard tests |
| Type check + production build | `npm run build` | ✅ clean (`tsc -b` + vite build) |
| Browser: doctor↔patient round trip | `scripts/browser_verify_doctor_patient.py` (real Chromium) | **14/14 PASS** — `docs/doctor-patient-verification/BROWSER_DOCTOR_PATIENT.json` |
| Browser: existing workspace regression | `scripts/browser_verify_workspace.py` | **15/15 PASS** — `docs/workspace-verification/BROWSER_WORKSPACE.json` |
| Frozen baseline integrity | digest check vs `docs/enhanced/BASELINE_MANIFEST.json` | 26/26 files + 120/3000 rows unchanged |

Browser round trip covers the mandatory integration list: doctor signs in (full original nav intact),
doctor sees patient-submitted daily records, uploads document, creates follow-up, marks review; patient
signs in (only 3 nav items), sees the follow-up/plan/document, downloads the document, submits + corrects
a daily log (edited chip), reports a missed dose with reason; doctor sees the round-trip results;
403s verified from the patient's own live session; 390 px mobile no-overflow for both shells.

## 5. Changed / new files

**New (17):**
```
backend/app/migrations/004_patient_records.sql
backend/tests/test_patient_records.py
frontend/src/workspace/PatientShell.tsx
frontend/src/workspace/PatientHome.tsx
frontend/src/workspace/Records.tsx
frontend/src/workspace/Documents.tsx
frontend/src/workspace/PatientDash.test.tsx
frontend/src/workspace/__fixtures__/patient-{home,daily-logs,medications,adherence,documents,follow-ups,sputum}.json
frontend/src/workspace/__fixtures__/doctor-{daily-logs,documents,follow-ups,adherence}.json
frontend/src/workspace/__fixtures__/audit.json
scripts/browser_verify_doctor_patient.py
docs/DOCTOR_PATIENT_UPGRADE_PLAN.md
docs/DOCTOR_PATIENT_DELIVERY.md
docs/doctor-patient-verification/** (evidence + screenshots)
```

**Modified (behaviour-preserving, additive):**
- `backend/app/workspace/service.py` — demo seeding + daily logs/medications/adherence/documents/follow-ups/audit/patient-home methods; audit hooks added to plan/review/sputum writes; patient cross-patient guard on every scoped list method.
- `backend/app/workspace/routes.py` — new `/api/workspace` routes (patient/home, patient/*, patients/{pid}/daily-logs|medications|adherence|documents|follow-ups|audit, documents/{id}/file, follow-ups/{id}, daily-logs/{id}/review).
- `frontend/src/App.tsx` — one conditional: patient role renders `PatientShell` instead of the clinician shell (doctor path untouched).
- `frontend/src/workspace/Profile.tsx` — two extra doctor tabs.
- `frontend/src/workspace/types.ts`, `frontend/src/workspace/workspace.css`, `README.md`, `docs/IMPLEMENTATION_SUMMARY.md`.

## 6. Security decisions
- No new dependencies; uploads reuse the base64+SHA-256 pattern (no multipart).
- Documents: MIME allowlist (pdf/png/jpeg/webp/plain), ≤1.5 MB, executable-extension denylist,
  magic-byte signature verification, SHA-256 stored + recomputed on read, bytes only via
  `/api/workspace/documents/{id}/file` with assignment check + `nosniff` + attachment disposition.
- Patients cannot write doctor-owned resources (medications, documents, follow-ups) — 403 verified.
- Corrections are audited, never silent; review/completion actions are immutable (409 on repeat).
- No secrets/passwords/tokens in frontend source, logs, or the archive (archive scanned).
- Demo-grade auth is honestly labelled — no regulatory compliance is claimed.

## 7. Known limitations (honest)
- Daily entries are self-reported documentation — no clinical validation or diagnosis.
- Multi-patient patient accounts aren't created in seeds (one patient account demonstrates the link;
  the schema + scoping support additional assignments without redesign).
- Care-plan visibility for the patient is read-only summary; patients can't comment on plans.
- SQLite persistence on hosted platforms (Render free tier etc.) depends on disk configuration —
  verify your deployment volume before relying on durability; local file storage `data/` +
  `PRANAGUARD_DB` documented in README.
- Playwright + Chromium is an optional dev dependency for the browser scripts (installed separately).

## 8. Deployment notes
Unchanged: uvicorn for the API, `npm run build` static assets, proxy `/api`+`/docs`+`/openapi.json`.
Set `PRANAGUARD_DEMO_*` passwords before first boot to override demo credentials; set `PRANAGUARD_DB`
to a writable path; run `/docs` to inspect the new routes. No new env vars are required.
