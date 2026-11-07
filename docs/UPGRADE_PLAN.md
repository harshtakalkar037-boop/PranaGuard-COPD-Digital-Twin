# PranaGuard platform upgrade — audit + implementation plan

Base: delivered `PranaGuard-Enhanced-v3.zip` (SHA-verified), extracted to a persistent workspace copy. Original repo and all prior ZIPs are untouched. Scientific identity preserved: 120 frozen synthetic patients/3,000 states, v1 models, rejected v2 evidence, active experimental v3 48h model — none are refit, relabeled or overwritten.

## Audit findings (actual codebase, 2026-11-07)

**Present**
- FastAPI backend (`main.py`, TwinEngine replay, SQLite Store with checksummed migrations 001–002), original research workspace (overview, twin, explanations, what-if, validation, replay, alerts + intervention logging), v2/v3 study evidence, read-only v3 48h API.
- Enhanced services: fictional registry (idempotent onboarding, 72h baseline tracking, manual observations, review→intervention ledger), 4 simulated device kinds with validated ingestion + tokens, 4-city environment with cache/fallback, notification centre (5 states + history + legacy-alert sync), email outbox (disabled by default), provenance. 12-item sidebar; polished green PranaGuard design.
- Tests: 119 backend, 50 frontend, production build; all previously verified.

**Genuinely missing**
- Any real authentication, doctor/patient roles, assignment scoping, per-doctor cohort (only an optional admin token on writes). The request's premise of "doctor login succeeds but /api/overview 403s" does not match this codebase — there was no login at all; this is built fresh, honestly scoped.
- One canonical patient *directory* (registry page is fictional-registration oriented; twin list lives on the overview).
- A persistent care-review workflow with states, follow-ups, queue and timeline ("activity" page logs alerts/interventions only).
- Care plans; sputum/symptom diary with optional photo attachment; consolidated activity/adherence view.
- Status-aware frontend error handling (all failures surface as raw messages/generic "Backend unavailable").

**Constraints discovered**
- `frontend/src/styles.css` and `frontend/src/components.tsx` are hash-protected original files — new styling goes to a new stylesheet; new UI uses existing components where possible plus new ones in new files. Palette/brand identity preserved.
- `engine.cohort()` has no assignment filter; extended with an optional `patient_ids` parameter without changing default behaviour or existing tests.
- New registrations for non-historical patients never get model predictions (72h rule) — kept, and directory must show baseline progress honestly instead of fake risk.

## Phases

1. ✅ Audit + this plan.
2. Backend workspace module (`backend/app/workspace/`): PBKDF2 demo users (2 doctors, 1 patient viewer), bearer sessions, additive migration 003 (`care_users, care_sessions, patient_assignments, care_reviews, care_review_events, care_plans, care_plan_revisions, sputum_entries, attachments`), doctor-scoped cohort (`engine.cohort(patient_ids)`), unified directory (search/city/origin/risk/sort/pagination), patient aggregate profile, care-review workflow (new→awaiting→under review→follow-up scheduled→completed→closed, validated transitions, event timeline, follow-up dates), care plans + revision history, sputum diary + capped image attachments, activity/adherence aggregation from real manual/device/monitoring records, two-doctor isolation (403). Original routes untouched.
3. Frontend: sign-in screen (demo identities, honest labels), status-aware errors, compact grouped sidebar (same items, regrouped; hash back-compat), unified Patient directory + onboarding reuse, patient profile tabs (overview/trends/sputum/plan/reviews/notifications), Care Action Centre (summary metrics, queue, workspace, timeline), plan editor, sputum diary with attachment upload, activity adherence charts — all reusing brand palette/components, all actions persisted.
4. Tests: backend suite additions (auth, scoping, isolation, workflows, persistence-across-reopen, attachment bounds, validation); frontend suites incl. workspace flows; updated App test harness for the session bootstrap; production build; full test runs.
5. Docs: rewritten README run/config/limits, `docs/IMPLEMENTATION_SUMMARY.md`, credentials/env docs (demo only, no secrets), verify local doc links.
6. Package complete runnable ZIP with manifest/hash checks of *protected original science files*, extracted-archive smoke test, deliver via file viewer.

Not claimed anywhere: clinical validity, real monitoring, real hardware, treatment effects, deployed production. Same-generator synthetic evidence only.
