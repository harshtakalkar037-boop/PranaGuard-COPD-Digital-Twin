> **Snapshot note:** The audit below was recorded before the subsequent hardening. Temporary credentials now expire and are single-use, eight original per-patient methods are individually scoped, and the original cohort reads are filtered before aggregation. See `ROUTE_PERMISSION_MATRIX.md` and `FINAL_RELEASE_READINESS.md` for current status.

# Final integration audit — before further implementation

Branch `arena/74d3a29f-pranaguard-copd-digital-twin` is active at base commit `f66d4eec02a40b01d8051a2d00d629c4c21a041b`. The integration changes are uncommitted and must be retained; no reset, merge, or production change has been made. This checkout has only that commit visible in its current local history. `docs/INTEGRATION_PROGRESS.md` and the existing changed frontend/backend files were reviewed before this follow-on work.

## Preservation

Direct inspection found **120 unique synthetic profile IDs** and **172,800 hourly rows**, with the same 120 IDs in both sources. `data/patients.json`, `data/synthetic_longitudinal.csv.gz`, `data/generation_manifest.json`, and `artifacts/models.joblib` all hash identically to `HEAD`; the research engine, model feature code, risk thresholds and bundled weather cache have no working-tree changes. The 120-patient historical engine remains separate from newly registered fictional records. These checks do not prove live production integrity.

## Route and authorization inventory

- Public in portal mode: `GET /api/health`, `POST /api/portal/register`, `POST /api/portal/login`; FastAPI documentation is also public. Patient registration creates an unlinked account only.
- Protected portal routes: password/logout/me; doctor assignment list and review queue/summary; per-patient detail/environment/explanation/scenario, sputum, care plan, daily-care and review routes; patient-owned check-in/upload/sputum/daily-care submission; per-user notifications and private upload download. Roles, ownership and assignments are enforced by dependencies and database checks, but need full method-by-method negative tests.
- Original `/api/overview`, `/api/patients...`, `/api/alerts...`, `/api/validation`, `/api/status`, `/api/replay...` and `/api/enhanced/*` require a doctor with access to **every synthetic database patient**, because several lists, global operations and IDs are unscoped. A legacy write token is additionally checked when configured. This is a conservative gate, not per-record authorization: registration or concurrent changes can block another doctor. WebSocket `/api/ws` is disabled in portal mode; isolated unsafe legacy mode disables the portal and has an unauthenticated stream.
- Route declarations and methods are in `backend/app/main.py`, `backend/app/enhanced/routes.py` and `backend/app/portal.py`; a route-permission matrix and comprehensive direct-request tests remain outstanding.

## Security and workflow gaps

Newly issued onboarding/reset passwords are generated randomly and stored using salted scrypt; startup does not overwrite existing hashes. They currently **do not expire**, and the same temporary credential can create multiple sessions before password change. Password change revokes sessions, but temporary-credential expiry and single-use semantics require additive migration and safe legacy handling. Browser-held bearer tokens are exposed to injected JavaScript. Public registration and login have no abuse throttling; trusted proxy request limits, CSP, malware scanning, account verification, secure cookie design and independent security review remain production blockers. Care and research are combined in the doctor dashboard; full five-patient workflow coverage, complete responsive/accessibility review and robust scoped legacy authorization remain unfinished.

## Environment and reproducibility

Code inspection found Open-Meteo/CAMS plus historical cached files; no QWeather integration or QWeather configuration was found in the repository. Live provider access or production environment variables have not been verified. The `frontend/vercel.json` rewrite names a Render API host, while README references a different host; this does not establish actual deployment routing. Production disk persistence, database backups, credentials, actual accounts, CORS, provider configuration, migrations and end-to-end journeys remain unverified.

`pyproject.toml` requires Python >=3.13; the installed system interpreter is 3.11.2. Previous local tests used compatible unpinned packages, not `requirements-lock.txt`. The reported backend failure is the protected CSS manifest: `frontend/src/styles.css` at both `HEAD` and the working tree hashes to `c3fc6f4a…`, while the manifest expects `bb0c274c…`; the manifest names a different historical base commit that is not in the visible local history. This predates the current uncommitted changes. Do not silently suppress the test or rewrite evidence; investigate actual historical provenance and run the locked environment if it can be obtained safely.

## Immediate plan

Document explicit route permissions; add expiry/single-use credentials and scoped security tests with additive migrations; retain the fail-closed whole-workspace gate until any route-level alternative can be proven safe. Test all five accounts and original research workflows only against disposable local synthetic databases. Investigate the CSS baseline and reproducible Python environment. Prepare an honest final release-readiness report; do not deploy or claim production verification.

### Historical stylesheet baseline clarification

The manifest records commit `95a4e2b00fcb2d9df7210c6b87ecba171a0c4e91`'s stylesheet (`bb0c274cfa0aa9dc01dea89dc191b2008bf0cade1c4b1cd4c3e99bc4759d08de`). Commit `14bb7535de` intentionally inserted `"Inter Variable",` before `Inter`; the complete resulting file at the starting HEAD hashes to `c3fc6f4abf0a66e968e9514419cc6c5e7f8cbca32d0c30d7e76a92def7cf2939`. This predates the present integration work. The integrity test now explicitly checks that exact current hash, verifies the insertion appears exactly once, reverses it, and verifies the original manifest hash. All other protected files remain byte-identical to the manifest. The manifest is unchanged; this narrowly documented exception does not permit unrelated stylesheet changes.
