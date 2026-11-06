# Application audit and implementation tracker

Date: 2026-11-06. Starting commit: `df10ef194dc75b48bee3c6fad4662484ee634b31` on the current Arena branch. This is an initial, prioritized audit, not a claim that every page or live account has been exercised. Existing detailed evidence: [integration audit](FINAL_INTEGRATION_AUDIT.md), [release readiness](FINAL_RELEASE_READINESS.md), [permission matrix](ROUTE_PERMISSION_MATRIX.md), and [portal workflows](PORTALS.md).

## Live and deployment evidence

The deployed public landing page at https://prana-guard-copd-digital-twin.vercel.app/ was retrieved through the page-fetching service; it identifies synthetic data and links to doctor/patient login. https://pranaguard-api.onrender.com/api/health returned `status: ok`, synthetic true and model `pg-synthetic-v1` through that service. This does not establish the deployed revision, account access, authorization, workflow behavior, persistence or backup status. Direct sandbox TLS connections to both hosts failed; interactive live browser login, every control and hosted database/shell inspection were **not performed**. No production credentials were obtained or accounts changed. `frontend/vercel.json` rewrites `/api/*` to the Render host and other paths to `index.html`; runtime Vercel and Render settings remain unverified.

## Current source inventory and route map

| Area / routes | Current behavior and dependencies | Initial issues / required verification |
|---|---|---|
| `/`, `/doctor/login`, `/patient/login` | React `Portal.tsx`; public landing and session-based login/registration; `/api/portal/*`, `portal_users`, `portal_sessions` | Live account workflows unverified; no public doctor registration; login throttling, secure cookie/session hardening and account verification remain open. |
| `/doctor/dashboard` | `ResearchGate.tsx` plus `App.tsx`: original cohort, twins, replay, explanation, what-if, validation and enhanced navigation | Overview currently requires every historical twin assignment; partial doctors receive 403. Default selection uses global replay demo ID rather than assigned ID. Research and care navigation remain separate sections. |
| `#overview`, `#patient`, `#explain`, `#scenario`, `#validation`, `#activity`, `#status` | Original research APIs and SQLite states, alerts, scenarios and interventions; frozen models and synthetic data | Model validation is global and must remain full-cohort restricted. Unscoped replay/status remain fail-closed. Verify partial-cohort aggregate isolation, empty states and error messages. |
| `#registry`, `#devices`, `#environment`, `#notifications`, `#sources` | Enhanced services in `backend/app/enhanced`; registry, simulated device, environment cache, notification and provenance tables | Registry is assigned-scoped; devices/provenance remain single-doctor gated. City context is not personal exposure. Full patient-management unification remains unfinished. |
| `#care:*` doctor care | `Portal.tsx`, `DailyCare.tsx`; assigned patient API, review queue, care plans, sputum, daily care and portal notifications | Existing workflows are functional in prior local tests, but not every requested workflow state, search, sorting, export or screen has been audited. Separate Add Patient vs registry remains confusing. |
| `/patient/dashboard` | Patient-linked check-ins, sputum, daily care, uploads and shared reviews; portal tables and private files | Cross-account checks exist; full live, populated/error-state and screen-reader testing remains incomplete. |
| `/api/portal/*` | Session, role, link and assignment checks; migrations 003–006 | SessionStorage bearer tokens, login throttling, upload scanning, retention, independent security audit and production storage remain blockers. |
| `/api/*` research | Secure doctor middleware plus per-patient/scoped handlers and restrictive single-doctor whole-workspace gate for unscoped operations | Out-of-band assignment/admin changes require quiescing traffic for remaining pre-checks; no claim of comprehensive atomic isolation. Secure WebSocket is disabled. |

SQLite migrations 001–006 cover enhanced monitoring, environment retry, portals, daily care, audit and temporary credentials; the research engine creates the original patients/states/alerts/scenarios tables. SQLite and private uploads must be on durable, backed-up storage for any hosted use. Production mount and restore have not been verified. Historical environmental inputs are cached Open-Meteo/CAMS sources; optional current context uses the existing provider, not personal exposure.

## Prioritized issue register

- **Critical:** Partial doctor receives 403 for overview rather than an assigned-only cohort; insecure shortcuts would leak other patients. Preserve full-cohort validation gate and original research outputs. Add two-doctor, zero-assignment, non-synthetic and aggregate tests.
- **Critical:** Remaining whole-workspace operations are restricted to one fully assigned doctor; complete per-record concurrency and independent security review are outstanding. Never open a global operation to make the UI appear functional.
- **Critical:** Production persistence, uploads, backups, deployments, account linkage and live isolation are unverified. Do not run resets or modify production data.
- **High:** Research default selection uses replay demo patient even when not assigned; stale/query-string IDs and empty cohorts need safe handling.
- **High:** Research overview failure is rendered as backend unavailability even for HTTP permission failures. Distinguish HTTP, network and invalid-response errors.
- **High:** Research registry and care provisioning are separate experiences. Full canonical patient-management redesign and complete workflow semantics require further implementation and regression testing.
- **Medium:** Notification test/email, simulated devices, replay and provenance remain restricted in multi-doctor databases. Screen and action status should explain restrictions.
- **Medium:** Responsive/automated accessibility checks have historical local evidence, not a complete manual screen-reader, keyboard, zoom or live browser review.
- **Low:** Additional design-system and navigation consolidation requires preserving existing functionality and scientific/safety labels.

## Progress checklist

- [x] Record starting commit, source structure, local configuration and limited live public evidence.
- [x] Implement and test assigned-only historical overview/list and zero assignments without exposing global validation.
- [x] Select an assigned historical patient by default, clear an unassigned URL selection, and distinguish network/HTTP/invalid-JSON errors.
- [x] Run the backend/frontend suites and selected local browser journeys; broader manual and live testing remains open.
- [ ] Complete remaining page-by-page live and local interaction audit and all requested journeys.
- [ ] Unify patient management and finish care workflow requirements without fabricating data.
- [ ] Complete manual accessibility, concurrency/security and provider checks.
- [ ] Verify hosted infrastructure, backups, live authorization and deployment only with appropriate access; do not claim health endpoint is full verification.

This is a synthetic research prototype, not clinically validated or suitable for diagnosis, treatment or emergencies.

## Phase 1 implementation and verification (2026-11-06)

- The overview/list now compute assigned original synthetic IDs in the same SQLite read snapshot as states, trends and alert counts. Empty assignments return empty data; global demo-patient metadata is omitted for partial cohorts. Open-alert totals now count all matching alerts, not just the 500-row list limit. Both research and portal global validation endpoints require complete historical assignment. Patient-specific authorization remains in place. These changes are not a complete audit of all other routes or atomic session revocation.
- The research UI defaults to an assigned twin, clears an unauthorized URL selection after the assigned registry is loaded, explains the disabled replay gate, handles an empty cohort and distinguishes permission, network, HTTP and invalid JSON errors. The patient registry and care provisioning experiences are **not yet unified**.
- With local source-built Python 3.13.10 and pinned requirements, **122 backend tests passed** (one Starlette/httpx deprecation warning). The fallback Python 3.11 environment could not load the 1.9.1 scikit-learn model and was not used as evidence. Node 22.22.3: **65 frontend tests passed**, TypeScript/Vite build passed, npm audit found zero vulnerabilities. Hosted CI is not yet evidence.
- Disposable Chromium: two-doctor partial-cohort and empty-assignment flow passed, including reload, an unassigned URL, cross-doctor denial, both validation denials and disabled replay. Three axe/overflow scans passed on the partial twin screen. A separate full-assignment fixture passed 96 automated axe/overflow scans at 390, 768 and 1440px plus the scripted focus, error, reduced-motion, navigation and calibration checks. These are not manual assistive-technology testing or a WCAG compliance claim.
- Five disposable patient care journeys (PG-0001–PG-0005) passed provisioning, password change, check-in, photo/document upload, daily records, clinician review/follow-up, care-plan versions, notification, logout/revocation, cross-patient checks and mobile overflow. They were executed before the final minor registry-request deduplication; the partial-cohort and accessibility suites were rerun after it. Live production accounts were not tested.
- A deterministic disposable research snapshot matched starting HEAD byte-for-byte for the documented states, trends, validation, three explanations and one scenario. Frozen cohort/model paths matched HEAD; this is not exhaustive of every possible output. No database migrations or production changes were made.
- Initial accessibility harness setup missed a required environment variable; after correcting the test invocation it passed. An initial partial-cohort browser run raced navigation after logout; the harness now waits for navigation and passed on rerun. Initial frontend failures reflected intentionally changed error messages and an incomplete test mock; assertions/mocks were updated for the new HTTP-specific behavior, and the suite passed.

Remaining work includes canonical patient management, full care status/queue semantics, all-page interaction and visual audit, manual accessibility, complete role/object and concurrency testing, infrastructure/provider checks, CI and authorized live verification. This branch is an incremental phase and is not production-ready.
