# Enhanced edition: implemented / simulated / external / planned

| Feature | Implemented behaviour | Explicit boundary |
|---|---|---|
| Patients | Search ID/name/city; city/sex/onboarding/risk filters; pagination; fictional registration; backend UUID-derived IDs; idempotent requests; full profiles | Synthetic/demo only. No real identifiers, documents or records should be entered |
| Profile | Demographics, optional manual history/diagnosis/medication/clinician alias; baseline coverage; original model risks/history where available; simulated readings/trends; manual symptoms/adherence; device associations; monitoring versions; reviews; notifications; independent environment | Manual fields are fictional reference values, not confirmed diagnoses, prescriptions or first72h observations |
| New-patient baseline | Collects first72h hourly coverage and real elapsed observation span for SpO₂/heart rate/respiratory rate; fast samples do not become hours; no timestamp/backfill bypass | Even completed device-only baseline does not provide the full evaluated feature frame. New-patient inference remains unavailable, not zero risk |
| Original analysis | All120 original profiles, saved twin states,24/48/72h probabilities, native TreeSHAP, scenarios, cohorts, charts, alerts and summaries retained | Frozen models, splits, evaluations and experiments unchanged.72h AUROC0.3951 below chance; all horizons have zero sensitivity at0.35 |
| Device integration | Four generic capability types; association; explicit start/stop; configurable2–300s interval; backend generation; authenticated ingestion; timestamp/unit/range validation; duplicate/conflict checks; immutable monitoring versions | **Simulated only.** No Bluetooth/USB SDK, commercial brand compatibility, physical sensor, device certification or clinical use |
| Environment | Actual Open-Meteo/CAMS air/weather API; allowlisted4-city registry;15min default component cache; minimum5min request interval; exponential error backoff; timestamps; stale/current/historical/missing states | Modelled city-grid context only. AQI is U.S. AQI, not Indian CPCB NAQI. No live context enters frozen ML features |
| Notifications | Patient monitoring/environment/data quality/system; unread state; patient/category/status filters; reason/source; read/acknowledge/under-review/resolve/close; append-only timeline; test control | In-app demo workflow, not an emergency/clinical alerting service. Resolution does not assert recovery |
| Existing care activity | Original model alerts/actions retained; patient/status filters; source/reason/review timestamp; bidirectional notification linkage | Existing status`new` corresponds to notification`active`. Original API remains compatible |
| Email | Backend-only disabled/preview/SMTP modes; fixed demo recipient; explicit connectivity test; outbox; sanitized failures; rate limit | No automatic patient/model-alert email. Actual localhost SMTP capture tested; real inbox delivery not verified without authorized credentials |
| Provenance | Category classifications plus record-level value/unit/source/type/valid/retrieved/freshness/patient/missingness/model-input inclusion | No real clinical/physical-device observations exist; missing AQI/wind/hardware values remain missing |
| Persistence | Additive checksum-versioned migrations; insert-ignore cohort seeding; no normal-setup reset; safe explicit replay reset with source-review archival | Active simulations stop on backend restart. Explicit replay reset still recreates active original-cohort state versions; back up first |
| Visual identity | Original stylesheet, Tailwind configuration, shared visual components and font stack byte-preserved; new scoped CSS uses existing palette | Sidebar scrolling is added solely to accommodate new entries. No template, font library, gradient, glassmorphism or redesign |

## Planned / not connected
- CPCB/Data.gov.in station adapter: access, reachability and applicable terms not fully verified.
- IMD weather adapter: documented endpoint returned401/API key missing; no authorized key supplied.
- Real-device enrollment, Bluetooth/USB integration and independent device validation.
- Compatible preprocessing and separately evaluated new-patient inference.
- Production identity/RBAC, consent, clinical governance, regulated retention and emergency response.
- SMTP credentials and actual externally verified inbox delivery.
- Remote publication/deployment of this enhanced edition. The original supplied README URLs remain historical references only.

## Scientific interpretation (unchanged)
No clinical validity or benefit is established. What-if outputs are noncausal sensitivity analyses. TreeSHAP explains raw model scores, not calibrated probabilities directly; the negative72h calibration slope can reverse direction. These enhancements demonstrate data handling and software workflows, not improved model performance or real-patient safety.
