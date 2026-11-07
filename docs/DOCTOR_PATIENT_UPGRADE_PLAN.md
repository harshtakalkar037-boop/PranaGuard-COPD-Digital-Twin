# Upgrade plan — connected Doctor Dashboard + Patient Dashboard

Source of truth: `PranaGuard-Enhanced-v4-Workspace.zip` (the previous delivered ZIP; re-extracted and
re-verified: 132/132 backend tests, 63/63 frontend tests pass before any change).

## Audit findings (already satisfied by the base — do NOT rebuild)
- Auth, roles (doctor/patient), PBKDF2 120k passwords, 12 h sessions, forbidden-token hashing, login 401s.
- Doctor scoping + assignment isolation; `/api/overview` doctor-scoped edition lives in workspace router.
- Sputum diary (colour/volume/consistency/cough/breathlessness/notes/photo attachment ≤512 KB + review
  flag), care plans with revision history, review workflow with timeline + follow-up dates.
- Original 26 protected files + frozen cohort intact; original 13-nav research/clinician sidebar intact.

## Gaps closed by this upgrade (additive only)
1. **Patient dashboard shell** — role-based sidebar: exactly 3 new primary items (Patient Home, My Health
   Records, Clinical Documents) for patient role; doctor nav unchanged (full existing navigation).
2. **Daily wellbeing log** — hydration (mL), food/nutrition notes, activity minutes, sleep hours/quality,
   general wellbeing, free notes + one-per-day-per-edit audit trail (in-place edit; full before/after
   snapshot in `audit_events`; patient may only touch own rows).
3. **Medication adherence** — `plan_medications` table (doctor-authored only), patient logs doses as
   taken/as-prescribed/missed with reason; unknown medication name rejected (422).
4. **Clinical documents** — doctor upload (title/type/date/notes + base64 payload ≤1.5 MB,
   allowlist MIME pdf/png/jpeg/webp/plain, executable-extension denylist, magic-byte check, SHA-256),
   scoped list/download/delete; patient read-only view of own record.
5. **Follow-ups & instructions** — dedicated `follow_ups` entity (doctor creates instructions + due date,
   completes/cancels); patient sees them with reminders on Patient Home.
6. **Reviewed flags** — doctor marks daily logs/sputum reviewed; patient sees who/when.
7. **Patient home aggregate** — today status, streak, upcoming follow-ups, latest plan summary, document
   count, reviewed badges.
8. **Demo seeds** — one-to-one demo link pat-pg0071 ↔ dr-atlas + 3 example daily logs, 2 adherence
   entries, 1 scheduled follow-up, 1 demo text document with provenance (idempotent; first-boot only).
9. **Audit events** — single `audit_events` table; every create/edit/review/upload/delete writes actor,
   role, action, entity, patient and before/after snapshots.
10. **Verification** — new backend suite (~16 tests), new frontend suite, extended Playwright browser
    run (doctor→patient→doctor round trip), README + delivery report, final ZIP re-verified.

## Guardrails kept
Frozen science untouched; no new deps (uploads reuse the base64+SHA-256 pattern already used for sputum
photos — no python-multipart); no clinical claims; documents are record-keeping, never AI diagnosis;
synthetic labels everywhere; additive migration 004 only.
