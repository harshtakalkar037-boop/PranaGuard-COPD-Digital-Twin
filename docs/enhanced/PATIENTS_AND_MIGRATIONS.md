# Fictional patients,72-hour onboarding and safe persistence

## Register and inspect
1. Open **Patients** (the original **Cohort overview** and **Patient twins** remain historical-model views).
2. Search patient ID/name/city or filter city, sex attribute, onboarding state and historical risk. New registrations show risk unavailable.
3. Choose **Add fictional patient**. Enter an alias rather than a real identity, demo age18–100, sex and one of the configured cities. Optional COPD/diagnosis/medication fields are explicitly fictional context, not clinical records. Assigned clinician is an explicitly fictional alias; no real clinician or advisor is implied.
4. Confirm all entered data are fictional. The server creates`PG-DEMO-…`; clients cannot choose/overwrite an existing ID. Request IDs are unique and payload-hashed: exact retries return the same patient, changed content under the same ID returns409.
5. Inspect the profile. It includes the manual references, baseline gate, original historical model section (only for the original cohort), device readings/chart, monitoring-version selector, symptoms/adherence form, existing intervention ledger, notification history and independent city context. **Export profile** downloads the selected profile, not an unrelated original twin.

## Warm-up is not a sample counter
- Manual reference values count as zero collected baseline hours.
- Device observations require explicit timezone, must not be future-dated beyond the small clock-skew allowance and cannot precede device registration by more than2 minutes. No public API accepts a creation-time/backfill override.
- First observation defines a72h window. Coverage is counted as distinct hour-offset bins for SpO₂, heart rate and respiratory rate; all72 bins and at least72 elapsed observed hours are necessary. Two-second simulation is still two-second wall-clock collection, not accelerated hours.
- The progress panel reports partial stream coverage, not model eligibility. Its partial means are monitoring summaries, **not** replacements for the frozen original first72h median baselines.
- Even complete baseline collection is insufficient for new inference: generic sensors do not supply the full aligned clinical/static/symptom/adherence/sleep/environment frame used by the saved model. New registrations therefore remain`prediction_supported:false`, with no manufactured24/48/72h probabilities.
- Original patient baselines, predictions and TreeSHAP remain tied to the frozen historical dataset. Monitoring overlays and manual observations never change them.

The automated72-hour eligibility test uses a clearly marked test-only clock fixture in a throwaway DB. This does not simulate waiting72 actual hours and is not a public bypass.

## Additive schema
`Store.apply_migrations()` runs checked-in SQL in transactions and records version/name/SHA256/applied time in`schema_migrations`. A changed previously applied migration fails explicitly; append a new migration instead. No automatic migration drops/resets/overwrites original tables.

- `001_enhanced_monitoring.sql`: registrations, devices, ingestion events/readings, monitoring states, manual observations, notifications/timeline, email outbox, environment cache/attempts and enhanced audit.
- `002_environment_backoff.sql`: adds failure count and next-retry time without changing source values or attempt timestamps.

Existing `patients`, `states`, `alerts`, `interventions`, `scenarios` and`meta` are retained. Original cohort seeding uses`INSERT OR IGNORE`, not replacement. New reviews use the existing intervention table, with monitoring-only versions explicitly distinguished in audit metadata.

## Backup before upgrade
Stop the backend and use SQLite's backup API (also includes committed WAL data):

```bash
python - <<'PY'
import sqlite3
from datetime import datetime,timezone
source=sqlite3.connect('data/pranaguard.sqlite')
name='data/pranaguard-backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite'
with sqlite3.connect(name) as destination: source.backup(destination)
source.close();print(name)
PY
```

Normal setup: `python -m scripts.bootstrap` **without**`--reset`. Existing DBs are not re-primed. A completely new DB can initialize the original historical demonstration; no training/network is needed.

## Explicit replay reset
The original reset control remains available only in historical-analysis views and requires confirmation. It recreates active original-cohort twin versions. It archives source alerts/interventions/scenarios in`enhanced_audit` and records closure history before deleting active-run records; alert IDs are no longer reused. New registrations, device records, manual observations and their reviews are preserved. Profiles expose archived source review records. Reset does not assert recovery and is not an onboarding shortcut. For complete recovery of a prior active-run state/version sequence, restore your database backup while the server is stopped.

`MIGRATION_PRESERVATION.json` records actual before/after table row digests for the supplied120-patient/3000-state database. Browser/destructive regression tests use a separate verification DB, never the delivered preserved snapshot.
