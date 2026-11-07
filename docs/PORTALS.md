# Connected research portals

> See `ROUTE_PERMISSION_MATRIX.md` for current scoped routes, the restrictive single-doctor gate, and limitations.

## Scope and safety

The new `/`, `/doctor/login`, `/doctor/dashboard`, `/patient/login` and `/patient/dashboard` experiences use the existing FastAPI process and SQLite Store. Migration 003 adds accounts, sessions, explicit patient links, doctor assignments, check-ins, private uploads, reviews and per-user notifications. Every patient access is checked on the backend; patient identity for check-ins and uploads comes from the session. No cohort or model is regenerated. All data must be synthetic; this is not a clinical service.

The original dashboard APIs were designed for an isolated synthetic demo. In secure mode, a doctor session is required, assigned synthetic records are scoped where implemented, and remaining unscoped operations require the restrictive single-doctor whole-workspace gate. The legacy WebSocket is disabled. Set `PRANAGUARD_UNSAFE_LEGACY_DEMO=1` only for a separate throwaway database and isolated legacy demo; this disables portal APIs and removes research isolation. Never expose that mode on a public network.

## Setup and migration

Use Python 3.12+ (the repository's pinned NumPy requires it) and Node 20.19+ or 22.12+. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the existing FastAPI backend. On first backend start, Store applies checksum-verified SQL migrations, including `003_portals.sql` through `007_followup_completion.sql`, transactionally. Existing databases are preserved; back up SQLite with its backup API before upgrading, and back up the private uploads directory together with it. Do not run replay reset, data-generation or training scripts as a migration. Set `PRANAGUARD_DB` consistently for the server and administration commands. The default is `data/pranaguard.sqlite`; if absent, the existing engine initializes the cohort from existing synthetic artifacts. Uploads default to `private_uploads/` (Git-ignored); configure `PRANAGUARD_UPLOAD_DIR` for a private persistent directory outside any web-served tree.

## Provision and test

1. Start the backend once to initialize the synthetic cohort. From a trusted local shell with the same database and activated venv, run:
   ```sh
   python -m backend.app.portal_admin create-doctor doctor1
   ```
   Enter a 12–128 character password twice. Doctor registration is not public.
2. At `/patient/login`, create a patient account and sign in. It is unlinked. In the trusted shell, explicitly select the correct **synthetic** record and assign the doctor:
   ```sh
   python -m backend.app.portal_admin link patient1 PG-0001 doctor1
   ```
   This checks account roles and the existing record, then links and assigns atomically. Duplicate links fail rather than replacing a mapping. Registration and login never create or assign a record. For synthetic records, the trusted local administrator can also use `assign-synthetic` (see the demo setup below). General assignment and unlink management are not implemented as a UI.
3. As patient, submit a check-in and upload a JPG/PNG photo or PDF/JPG/PNG care plan (10 MB maximum). The assigned doctor receives in-app notifications.
4. As doctor, select the assigned record in Care Action Centre, review the check-in/upload, record status, notes, optional follow-up and date. Tick **Share** only for information appropriate for the patient. The patient sees shared updates and receives an in-app notification. The doctor can see supported synthetic 24/48/72-hour estimates and historical observations.
5. Mark a notification read and reload to verify persistence. Sign out to revoke that session. Use two accounts and assignments to test isolation.

## API overview

All endpoints below are under `/api/portal`. `POST /register` creates only patients; `POST /login` returns an eight-hour opaque bearer token; `POST /logout` revokes it; `GET /me` returns the account and optional link. Protected endpoints require `Authorization: Bearer <token>`.

- `GET /patients`: assigned patients for doctors only. `GET /validation` requires assignment to all original historical synthetic twins; `GET /patients/{id}/explanation` and `POST /patients/{id}/scenarios` require assignment to that patient.
- `GET /patients/{id}` and `/patients/{id}/environment`: owner or assigned doctor. Patient responses omit model details and unshared reviews.
- `POST /checkins`: patient derived from session; strict symptom fields; assigned doctors notified transactionally.
- `POST /uploads`: multipart `kind`, `file`, optional `description`. Extension and magic signature validated; random disk name. `GET /uploads/{id}` checks ownership or assignment, returns an attachment with `nosniff`, and never reveals storage paths.
- `POST /patients/{id}/reviews`: assigned doctor only; optional check-in/upload associations checked against the same patient; shared updates generate notifications.
- `POST /patients/{id}/reviews/{review_id}/complete-followup`: assigned doctor records a private completion note once; the original review remains unchanged and the completion is audited.
- `GET /notifications` and `POST /notifications/{id}/read`: account-scoped history and persistent read status, filtered by current patient link/assignment.

## Security and limitations

Passwords use salted scrypt; only SHA-256 token hashes are stored. Tokens expire and can be revoked; the browser keeps them in session storage. Uploads use random filenames, private storage, restrictive file permissions, signature checks and download authorization. Session storage is accessible to injected JavaScript. TLS, a hardened CSP, secure HttpOnly cookies or equivalent, login throttling, request-body limits at a reverse proxy, malware scanning, encryption, account recovery, monitoring and independent security review are required before handling sensitive data. Doctor identity verification, record-link consent, MFA, management audit UI, retention and regulatory controls are not implemented. Public registration is not abuse-resistant. Do not store real patient information. SMS and email are not part of the new portal.

Predictions are unchanged and evaluated only on synthetic outcomes, with weak performance including below-chance 72-hour discrimination. They are not a diagnosis or clinical guidance. Environmental context uses the existing provider/cache with source, retrieval and freshness indicators; it is city-grid context, not personal exposure. Historical fallback is not current weather. Photos are not automatically analysed.

## Tests

Run `pytest backend/tests -q`, then `cd frontend && npm test && npm run build`. Legacy tests run in isolated demo mode. Portal tests cover access isolation, authentication/logout, check-ins, notifications, shared review, file validation/download authorization and repeatable migrations. Browser automation is provided for an isolated disposable demo; see the completion report. These tests do not replace penetration, clinical, full accessibility or load testing.

Verification results and changed-file inventory: [docs/PORTAL_RESULTS.md](docs/PORTAL_RESULTS.md).


## Daily care and controlled synthetic-demo provisioning

Use a separate, disposable synthetic-only database and private upload folder. **Never use this synthetic-only provisioning on a public network or for real users.** For example, from the repository root with the venv activated:

```sh
mkdir -p demo/uploads
export PRANAGUARD_DB="$PWD/demo/demo.sqlite"
export PRANAGUARD_UPLOAD_DIR="$PWD/demo/uploads"
export PRANAGUARD_SYNTHETIC_DEMO_PROVISIONING=1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start the backend once to initialize existing synthetic profiles. In another trusted local shell using the same `PRANAGUARD_DB`, create a doctor and assign existing synthetic records:

```sh
export PRANAGUARD_DB="$PWD/demo/demo.sqlite"
python -m backend.app.portal_admin create-doctor demo_doctor
python -m backend.app.portal_admin assign-synthetic PG-0001 demo_doctor
python -m backend.app.portal_admin assign-synthetic PG-0002 demo_doctor
python -m backend.app.portal_admin assign-synthetic PG-0003 demo_doctor
```

Log in as that doctor. On **Add Patient**, choose an assigned synthetic record and provision its account. The one-time screen shows the patient ID and temporary password; convey it securely. The initial password is randomly generated and provisioning is enabled only by the explicit synthetic-demo switch. The patient must change it before accessing records. The temporary password expires 24 hours after issuance and can be used for only one sign-in; its restricted session expires no later than the credential. If that session is lost, an administrator must issue a fresh credential. Provisioning is disabled by default and never creates or assigns arbitrary records. An existing patient account can instead be linked via the `link` command. For a forgotten password, a trusted local administrator can run `python -m backend.app.portal_admin reset-password USERNAME`; it prints a random temporary password once, revokes existing sessions, and requires another change. The CLI is not an online recovery service.

The patient can use **Sputum Diary** to record and edit observations with private optional photos; edits retain prior snapshots and reset review status. **My Daily Care Plan** contains the active doctor-entered plan and meal, water and activity records. Clinicians can enter and deactivate plan versions, review records, and share updates. Date filters use UTC; daily progress is calculated in the browser's local date. No hydration target or exercise prescription is generated by the application. Notifications are in-app only.

### Reset only the disposable demo

Stop the demo backend first. Verify that `demo/demo.sqlite` and `demo/uploads` are the disposable paths created above, **not** an existing or valuable database. Back up anything needed. Then remove only those demo files:

```sh
rm -f -- "$PWD/demo/demo.sqlite" "$PWD/demo/demo.sqlite-wal" "$PWD/demo/demo.sqlite-shm"
find "$PWD/demo/uploads" -maxdepth 1 -type f -delete
```

Restart and repeat provisioning. This irreversibly deletes only that demo's accounts, activity and uploaded files; never use it against the original cohort database. `demo/` is ignored by Git. Existing model/data artifacts are not regenerated or changed.

### Browser test

`frontend/e2e/connected-care.mjs` exercises the actual UI and API and intentionally creates data. Run it only against a fresh disposable demo with synthetic provisioning enabled, a doctor already created, `PG-0001` assigned but not yet linked, and a local Chromium installed:

```sh
cd frontend
E2E_BASE=http://127.0.0.1:5173 E2E_DOCTOR=demo_doctor \
E2E_DOCTOR_PASSWORD='<local test password>' E2E_CHROMIUM_PATH=/path/to/chromium \
npm run test:e2e
```

Do not commit test credentials. The script provisions `PG-0001` and cannot be repeated against the same demo without resetting it. Set `E2E_SCREENSHOTS` to an appropriate output directory if screenshots are desired.

### Research workspace access on the integration branch

The original research APIs include unscoped operations. In secure portal mode, these remaining unscoped operations require a doctor session, a database with **exactly one doctor**, assignment to **every existing synthetic record**, and no non-synthetic profiles. The single-doctor condition is intentionally restrictive: without it a second doctor could create a record between a whole-workspace authorization check and an unscoped read. This does not protect against administrative changes made outside the application while a request is in flight; quiesce traffic for all user, assignment, patient and schema administration. The original `/api/overview` and `/api/patients` return only assigned historical synthetic twins, including empty cohorts; aggregates and trends use that same population. The global `/api/validation` and `/api/portal/validation` require assignment to every original historical synthetic twin. The eight original per-twin methods require assignment to the historical twin. Enhanced registry list, detail, observations and reviews enforce synthetic record assignment, and registration assigns its creator atomically; original alert lists and updates are scoped to assigned synthetic records; city-grid context is doctor-only and independent of patient records. See the matrix for each method and optional write token. Patients and anonymous users cannot access research endpoints. A trusted local administrator may assign the original existing synthetic cohort without changing the records:

```sh
python -m backend.app.portal_admin assign-cohort "$DOCTOR_USERNAME"
```

A new fictional record is assigned to its registering doctor and is not automatically assigned to another doctor. Registry idempotency retries require assignment to the existing record. A second doctor blocks all still-unscoped workspace functions, even if both have every record assigned; historical and explicitly scoped functionality remains available. This is a usability and release blocker until each remaining operation is safely scoped and independently tested. The secure research workspace polls instead of using the legacy unscoped WebSocket. The optional JSON `PRANAGUARD_DEMO_BOOTSTRAP` can set `assign_cohort: true` to assign the original verified synthetic cohort, but it never changes an existing password hash. It does not replace a controlled administrator process. Never enable it or the legacy mode with real patient data.


Migration 006 does not change existing hashes or links. Accounts already marked `must_change_password` before this migration have no trustworthy issuance time, so their old temporary passwords and restricted sessions fail closed. A trusted administrator must deliberately run `reset-password` and securely convey a new 24-hour single-use credential. There is no automatic startup reset. Expired credentials are handled the same way. Protect CLI output from logs and terminal history. This is a synthetic demo workflow, not an online recovery service.

### Enhanced research notifications

The enhanced notification centre lists and counts only assigned synthetic patient events; detail and review enforce the same assignment and verify that a linked legacy alert belongs to that patient. Reviews check assignment in the write transaction. Shared city/system notices and the test/email controls remain available only with a single doctor assigned every synthetic record; they are hidden or denied in multi-doctor workspaces. The portal’s separate care notifications remain user-scoped.
