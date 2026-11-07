# Notification centre, legacy reviews and demo email

## Categories and lifecycle
Notifications are **in-app synthetic demonstration events**, not clinical/emergency alerts.

- `patient_monitoring`: original model replay alerts, simulated-reading demo rules and manual fictional observation rules.
- `environment`: current fresh modelled city context matching a demo threshold; no patient-exposure claim.
- `data_quality`: warm-up incomplete, stopped/stale/interrupted/error device streams, failed/stale external components.
- `system`: user-triggered test, sanitized background-service problems and explicit email-test results.

The header/sidebar unread badge comes from persisted backend counts and updates through WebSocket invalidation plus the existing15s REST fallback. Filters: patient, category, review status and unread-only. Latest200 matching records are displayed; the API supports up to500 per request and retains the entire SQLite history. Detail includes source, reason, classification, patient link, created/reviewed/source-valid times and append-only review timeline.

Reading is independent from review. States: `active`→`acknowledged`/`under_review`→`resolved`→`closed` (direct review/closure is also allowed). Resolved/closed items cannot be reopened into an active review. A new event should create a new notification. Read/unread changes are recorded. The shared demo actor is not authenticated clinician identity or a regulated electronic signature.

Choose **Create test notification** to demonstrate the lifecycle without inventing a patient condition. Mark read, acknowledge, enter a fictional note, mark under review, resolve and close. Resolution means only workflow completion, not recovery or successful treatment.

## Existing alert/action compatibility
The original `alerts` table/API and care-activity screen remain. Existing `new` corresponds to notification `active`; acknowledgement/resolution synchronizes in both directions. An under-review notification maps to acknowledged in the legacy three-state API. Closing maps to resolved. Links retain the original alert ID/state version/risk/horizon/source timestamp; new overlays do not generate a frozen-model risk.

Original care activity also has patient/status filters, source/reason/review timestamp and a working link to the unified category/history workflow. Profile reviews append to the same existing `interventions` ledger. An explicit replay reset archives source alert/review/scenario records and preserves notification review history rather than silently erasing it.

## Clearly unvalidated demonstration rules
- Simulated SpO₂≤92% or heart rate≥110bpm; deduplicated by device/hour.
- Fictional manual symptoms≥7/10 or adherence<50%.
- Fresh city-model PM2.5≥35µg/m³ or U.S.AQI≥100.
- Enabled stream stale after max(30s,3×interval); user stop/restart interruption/error; provider failure/stale timestamp.

These numbers are demonstration fixtures/rules, **not validated COPD safety or urgency thresholds**. No emergency contact, clinician task assignment, diagnosis, prescription or intervention is performed. The original model's0.35 cutoff and negative scientific findings are unchanged.

## Email: explicit test only
No automated email is sent from patient observations, environment rules, ML alerts or review actions. The only send path is the user's explicit **Run demo email test** / `POST /api/enhanced/email/test {}`.

Backend environment modes:
- `PRANAGUARD_EMAIL_MODE=disabled` (default): creates a truthful`not_sent_disabled`result; no network/send.
- `preview`: creates`preview_not_sent`outbox row; no SMTP/send.
- `smtp`: sends a fixed generic connectivity-test body to exactly one configured demo recipient. It contains no patient ID/name/readings/risk/note or attachment.

Configuration: `PRANAGUARD_SMTP_HOST`, `PORT`, `USER`, `PASSWORD`, `FROM`, `PRANAGUARD_DEMO_RECIPIENT`, `STARTTLS`, `SSL`. Keep all credentials in backend`.env`or hosting secrets; never commit them, put them in a VITE variable, print them or enter arbitrary recipients in the browser. API requests containing recipient overrides are rejected.

STARTTLS is on by default. SSL mode supports encrypted SMTP directly. Unencrypted SMTP is rejected except a deliberate localhost capture sink with`PRANAGUARD_SMTP_ALLOW_INSECURE_LOCAL=true`. It does not enable cleartext external SMTP.

The outbox persists pending/disabled/preview/failure/configuration-error/`accepted_by_smtp`results and sanitized descriptions. SMTP errors expose exception class only, not server text that could contain credentials/addresses. A transaction reserves the test before I/O and enforces30s between attempts. SMTP acceptance **does not verify inbox delivery**.

Actual localhost SMTP acceptance and body privacy were tested with a real socket-based capture sink. External provider authentication/recipient inbox delivery was not tested because no authorized credentials/recipient were supplied; do not claim it occurred.
