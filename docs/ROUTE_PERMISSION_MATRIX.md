# Route authorization matrix

Generated from the application OpenAPI route list and reviewed against handlers. Applies only with `PRANAGUARD_UNSAFE_LEGACY_DEMO` off (the default). Legacy mode intentionally disables the portal and removes the research isolation gate; never enable it for real or shared data. HTTP docs/schema are public metadata; `/api/ws` closes with policy code 1008 in secure mode. Unknown paths do not grant data access.

**S** = valid unexpired, unrevoked bearer session; **P** = S plus patient role and a linked record; **D** = S plus doctor role; **A** = S plus patient-own or doctor-assigned record (404 on failed record authorization); **D+A** = both doctor and assigned record. Pending temporary-password sessions can only access `/me`, `/password`, and `/logout`, until their deadline. **L** = D in a database with exactly one doctor, assigned to *every* existing DB patient, all profiles synthetic; this conservative whole-workspace gate precedes the remaining unscoped original/enhanced HTTP routes. It prevents another pre-existing doctor from creating a fictional record between an authorization check and an unscoped read. Administrative database changes must only occur with traffic quiesced: the check is not atomic against out-of-band changes. **H** = D assigned to every original synthetic twin with matching synthetic database profiles; aggregates, trend and alert counts are filtered to those original IDs before calculation and limits. **T** = the configured legacy `X-Demo-Token`, when configured, in addition to the listed doctor authorization. Ingestion also checks its device token. If T is not configured it adds no protection.

L is intentionally over-restrictive: a second doctor blocks unscoped research features even if both doctors have full assignment. Historical cohort/validation, assigned twin and registry methods, assigned alerts and enhanced notifications, and city context remain available under their explicit rules. It is not a substitute for per-record scoping of global routes. There is no general online administration API; the doctor-assigned synthetic demo provisioning endpoint is listed below, and local `portal_admin` requires trusted host access.

| Method | Route | Server-side requirement |
|---|---|---|
| POST | `/api/portal/register` | Public patient-only self-registration; account unlinked |
| POST | `/api/portal/login` | Public credential check; issue session or consume temporary credential |
| POST | `/api/portal/password` | S: own account; current password; revoke all sessions |
| POST | `/api/portal/logout` | S: revoke own token |
| GET | `/api/portal/me` | S: own account/link |
| GET | `/api/portal/patients` | D: assigned records only |
| GET | `/api/portal/patients/{pid}` | A: patient own or D assigned; patient sees shared reviews only |
| GET | `/api/portal/patients/{pid}/environment` | A: own/assigned patient city context |
| POST | `/api/portal/checkins` | P: own linked patient, ID inferred |
| POST | `/api/portal/uploads` | P: own linked patient; linked sputum entry must be own |
| GET | `/api/portal/uploads/{upload_id}` | A: upload’s own/assigned patient |
| POST | `/api/portal/patients/{pid}/reviews` | D+A: related submission IDs must belong to same patient |
| GET | `/api/portal/notifications` | S: own notifications only |
| POST | `/api/portal/notifications/{notification_id}/read` | S: own notification only |
| GET | `/api/portal/validation` | D: aggregate validation without patient ID lists |
| GET | `/api/portal/patients/{pid}/explanation` | D+A: assigned patient |
| POST | `/api/portal/patients/{pid}/scenarios` | D+A: assigned patient |
| POST | `/api/portal/sputum` | P: own linked patient, ID inferred |
| PUT | `/api/portal/sputum/{entry_id}` | P: own linked patient and own entry |
| GET | `/api/portal/patients/{pid}/sputum` | A: own/assigned patient; patient sees shared reviews only |
| POST | `/api/portal/patients/{pid}/sputum/{entry_id}/reviews` | D+A: entry must belong to selected patient |
| GET | `/api/portal/patients/{pid}/care-plan` | A: own/assigned patient; history doctor only |
| POST | `/api/portal/patients/{pid}/care-plan` | D+A: assigned patient |
| POST | `/api/portal/daily-care` | P: own linked patient, ID inferred |
| GET | `/api/portal/patients/{pid}/daily-care` | A: own/assigned patient; patient sees shared reviews only |
| POST | `/api/portal/patients/{pid}/daily-care/{log_id}/reviews` | D+A: log must belong to selected patient |
| POST | `/api/portal/patients/{pid}/provision-demo` | D+A: assigned synthetic patient and explicit demo switch |
| GET | `/api/portal/care-queue` | D: assigned patients only |
| GET | `/api/portal/doctor-summary` | D: assigned patients only |
| GET | `/api/enhanced/status` | L |
| GET | `/api/enhanced/registry/patients` | D: assigned synthetic records and counts only |
| POST | `/api/enhanced/registry/patients` | D + T: fictional record atomically assigned to creator; idempotent retry requires assignment |
| GET | `/api/enhanced/registry/patients/{pid}` | D+A: assigned synthetic record |
| POST | `/api/enhanced/registry/patients/{pid}/observations` | D+A: assigned synthetic record + T |
| POST | `/api/enhanced/registry/patients/{pid}/reviews` | D+A: assigned synthetic record + T |
| GET | `/api/enhanced/devices` | L |
| POST | `/api/enhanced/devices` | L + T |
| POST | `/api/enhanced/devices/{did}/start` | L + T |
| POST | `/api/enhanced/devices/{did}/stop` | L + T |
| GET | `/api/enhanced/devices/{did}/readings` | L |
| POST | `/api/enhanced/ingestion` | L + T + device token |
| GET | `/api/enhanced/environment/cities` | D: configured public city metadata |
| GET | `/api/enhanced/environment/{city}` | D: city-grid context, no patient record |
| POST | `/api/enhanced/environment/{city}/refresh` | D + T: refresh shared city context |
| GET | `/api/enhanced/notifications/counts` | D: counts only assigned synthetic-patient notifications, plus system notices only under L |
| GET | `/api/enhanced/notifications` | D: assigned synthetic-patient rows and counts scoped before limit; unassigned patient filter returns 404; shared system notices only under L |
| POST | `/api/enhanced/notifications/test` | L + T |
| GET | `/api/enhanced/notifications/{nid}` | D+A: assigned synthetic-patient notification; shared system notices only under L |
| PATCH | `/api/enhanced/notifications/{nid}` | D+A + T: assignment checked inside write transaction, linked alert must belong to same patient; shared system notices only under L |
| GET | `/api/enhanced/email` | L |
| POST | `/api/enhanced/email/test` | L + T |
| GET | `/api/enhanced/provenance` | L |
| GET | `/api/health` | Public health/model version only |
| GET | `/api/overview` | H: original historical cohort only |
| GET | `/api/patients` | H: original historical cohort only |
| GET | `/api/patients/{pid}` | D+A: assigned original synthetic twin |
| GET | `/api/patients/{pid}/history` | D+A: assigned original synthetic twin |
| GET | `/api/patients/{pid}/versions` | D+A: assigned original synthetic twin |
| GET | `/api/patients/{pid}/explanation` | D+A: assigned original synthetic twin |
| POST | `/api/patients/{pid}/scenarios` | D+A: assigned original synthetic twin + T |
| GET | `/api/patients/{pid}/scenarios` | D+A: assigned original synthetic twin |
| GET | `/api/alerts` | D: assigned synthetic patient alerts filtered before the 500-row limit; unassigned patient filter returns 404 |
| PATCH | `/api/alerts/{alert_id}` | D+A + T: alert owner assignment and synthetic status checked in the same write transaction |
| GET | `/api/patients/{pid}/interventions` | D+A: assigned original synthetic twin |
| POST | `/api/patients/{pid}/interventions` | D+A: assigned original synthetic twin + T |
| GET | `/api/validation` | H: frozen historical validation |
| GET | `/api/status` | L |
| GET | `/api/replay` | L |
| POST | `/api/replay/step` | L + T |
| POST | `/api/replay/start` | L + T |
| POST | `/api/replay/pause` | L + T |
| POST | `/api/replay/reset` | L + T |

## Non-HTTP and administration

| Interface | Requirement |
|---|---|
| WebSocket `/api/ws` | Disabled in secure mode: all connections close with 1008, including anonymous, patient and doctor. Unsafe isolated legacy mode has an unauthenticated stream and must not be used in a shared environment. |
| `portal_admin` CLI | Trusted host access only; no network administration API. Commands create a doctor, link/assign existing records, reset credentials or assign the original synthetic cohort. Quiesce application traffic when changing users, assignments, records or database schema. |
| Private uploads/download | Submission requires P and optional related diary ID ownership; download requires A for the upload owner. Files are kept outside the public web root. |

## Evidence and gaps

Automated route enumeration rejects anonymous, expired and revoked sessions for every protected HTTP method, and a patient session for every original/enhanced HTTP method. Eight explicitly enumerated original per-patient methods now require assignment to the synthetic historical twin rather than the whole-workspace gate; tests cover each method with a modified ID and unassigned doctor. Historical cohort tests insert an unassigned fictional state and 501 alerts and verify patient rows, filtered search, aggregate counts and trends remain unchanged, while other global routes remain blocked; registry list, detail, writes and idempotent retry also enforce assignment; alert tests cover another doctor’s 501 newer alerts, assigned/non-synthetic IDs, and updating an authorized alert older than 500 rows; city context is independent of patient records; a disposable browser test confirms the same isolation and unavailable-context warning. `backend/tests/test_portal.py` also exercises selected assigned/unassigned patient IDs, uploads, child record IDs, private/shared reviews, registration and password/session transitions. This is not yet a complete role × route × modified-ID matrix: handler-level negative cases and browser journeys remain incomplete. Server-side role checks can occur after request validation, so an invalid body may return 422 rather than 403 without executing the handler.

Unscoped L routes include replay, devices, test-notification creation, email, status and provenance. Legacy alerts and enhanced notification lists and reviews are individually scoped, including authorization before result limits and an assignment check inside the update transaction. Enhanced notification counts are scoped; shared system/city notices are hidden unless L holds, and the legacy-alert bridge on doctor reads is scoped and transactional. The remaining L routes stay locked behind complete synthetic-workspace assignment; do not infer isolation from a UI filter.

The internal simulator calls the same schema-validated, device-token-checked ingestion service directly; it does not issue an externally usable authorization bypass. The HTTP ingestion route retains L, T and the device-token requirement. Legacy WebSocket broadcasts remain confined to unsafe legacy mode.
