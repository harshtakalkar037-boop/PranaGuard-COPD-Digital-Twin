# Enhanced REST API (original routes retained)

Base prefix:`/api/enhanced`. FastAPI `/docs` and `/openapi.json` describe strict request validation. Requests reject unknown fields, nonfinite values and unsupported enums. All patients/observations are fictional. JSON errors explain validation or conflict; secrets are never included in status/ingestion responses.

## Access
- Existing optional shared `PRANAGUARD_ADMIN_TOKEN` protects **all enhanced write routes** with `X-Demo-Token`.
- Device ingestion also requires a per-device `X-Device-Token`; the backend-owned simulator supplies it internally. No public hardware-token provisioning is implemented.
- Reads/WebSocket remain public synthetic-demo endpoints. Configure a write token/origin allowlist before exposure; this is not production identity/RBAC.
- Browser requests use same-origin `/api`; Vite proxies backend requests/WebSockets. No browser code calls sandbox localhost. Public separate-host deployment can set only the public `VITE_API_BASE_URL`; provider/email/device secrets must remain backend-only.

## Routes
| Method | Path after prefix | Purpose |
|---|---|---|
| GET | `/status` | Enhanced counts, applied migrations, public configuration flags and security boundaries; no secrets |
| GET | `/registry/patients` | All original+registered profiles. `q`(≤100),`city`,`sex`,`status`,`risk` filters |
| POST | `/registry/patients` | Validate fictional registration; generate server ID; idempotent request ID |
| GET | `/registry/patients/{pid}` | Complete profile, baseline gate, historical model if original, monitoring/readings/versions, observations, existing reviews/archive, notifications and independent environment |
| POST | `/registry/patients/{pid}/observations` | Explicit fictional symptoms/adherence/note; no model inference |
| POST | `/registry/patients/{pid}/reviews` | Append a demo review to the existing intervention ledger |
| GET | `/devices` | Associations/capabilities/units; optional`patient_id`; no tokens |
| POST | `/devices` | Associate a generic simulated device; disconnected by default |
| POST | `/devices/{did}/start` | Explicitly start simulation with interval2–300s |
| POST | `/devices/{did}/stop` | Stop; do not delete readings/history |
| GET | `/devices/{did}/readings` | Persisted readings;`limit`1–1000(default100) |
| POST | `/ingestion` | Authenticated/idempotent simulated observation event |
| GET | `/environment/cities` | Central configured city registry |
| GET | `/environment/{city}` | Current/cache/stale/historical/missing independent air/weather context |
| POST | `/environment/{city}/refresh` | `{}`; checks TTL/backoff/rate policy; never bypasses minimum request interval |
| GET | `/notifications/counts` | Persisted unread/total/open counts with legacy bridge sync |
| GET | `/notifications` | Optional`patient_id`,`category`,`status`,`unread_only`;`limit`1–500(default200) |
| POST | `/notifications/test` | `{}`; create system test, not a patient condition |
| GET | `/notifications/{nid}` | Source/reason/metadata and append-only timeline |
| PATCH | `/notifications/{nid}` | `read`and/or`status`, optional fictional`note` |
| GET | `/email` | Public mode/configured flags and sanitized test outbox; no addresses/passwords |
| POST | `/email/test` | `{}` only; fixed backend-configured demo recipient; rate limited; no patient data |
| GET | `/provenance` | Optional`patient_id`,`city`; category/record/unit/type/time/freshness/missingness/model-input ledger |

Registry statuses:`historical_twin`,`baseline_not_started`,`collecting_baseline`,`baseline_collected_no_model`. Risk filters:`low`,`elevated`,`high`,`unavailable` (new patients have unavailable). Notification categories:`patient_monitoring`,`environment`,`data_quality`,`system`. Review states:`active`,`acknowledged`,`under_review`,`resolved`,`closed`.

## Minimal registration / device example
Use IDs returned by the actual responses; never guess an existing patient ID to overwrite it:

```python
import os,uuid,httpx
headers={'X-Demo-Token':os.environ['PRANAGUARD_ADMIN_TOKEN']} if os.getenv('PRANAGUARD_ADMIN_TOKEN') else {}
with httpx.Client(base_url='http://127.0.0.1:8000/api/enhanced',headers=headers) as c:
    r=c.post('/registry/patients',json={
        'request_id':uuid.uuid4().hex,
        'fictional_identity_confirmed':True,
        'demo_alias':'Atlas Example','age':58,'sex':'Not specified','city':'Pune',
        'source_type':'manual_demo'
    });r.raise_for_status();pid=r.json()['patient_id']
    r=c.post('/devices',json={'patient_id':pid,'kind':'pulse_oximeter','interval_seconds':5})
    r.raise_for_status();did=r.json()['id']
    r=c.post('/devices/'+did+'/start',json={'interval_seconds':5});r.raise_for_status()
    # Read actual accepted records after the configured wall-clock interval.
    r=c.get('/devices/'+did+'/readings');r.raise_for_status();print(r.json())
    c.post('/devices/'+did+'/stop',json={}).raise_for_status()
```

The simulator itself submits to ingestion through the same REST route. Ingestion shape (illustrative field names; IDs/timestamps must come from actual registration/runtime):

```text
patient_id: returned synthetic patient ID
 device_id: returned simulated device ID
 event_id: unique bounded alphanumeric/underscore/colon/hyphen identifier
 observed_at: timezone-aware ISO8601, no future/backfill bypass
 source_type: simulated_device
 readings: [{metric:spo2,value:95.5,unit:%}, {metric:heart_rate,value:77,unit:bpm}]
```

No arbitrary real-device/EHR source, provider URL, API key, physical compatibility flag, predicted risk or model-feature override is accepted. Duplicate events return the original monitoring version; conflicting duplicates409. Invalid capabilities/units/ranges/timestamps422. Wrong association409; missing per-device token401. New data from stopped simulations409.

## Registration optional fields
`copd_history`,`diagnosis_info`,`medications`(≤1000 chars each),`clinician_alias`(2–50 ASCII alias),`baseline_spo2`50–100,`baseline_heart_rate`25–240,`baseline_resp_rate`5–60,`fev1_pct`10–120,`bmi`12–50,`smoking_pack_years`0–150,`prior_exacerbations`0–15. These are bounded **demo** values, not validated clinical ranges or first72h observations. Age18–100; fictional alias2–50; city allowlisted. Manual observation:`fictional_data_confirmed:true`,`symptom_score`0–10,`adherence`0–1,optional`note`≤1000. Review:`kind`from original intervention categories,`note`3–2000.

## Model boundary
The original `/api/patients`, `/api/overview`, `/api/patients/{pid}`/history/explanation/scenario and replay/validation APIs still describe the original evaluated historical cohort. New registry patients deliberately do not appear as fabricated model twins in those endpoints. Use the registry API for their monitoring profiles. Live environment and device/manual data cannot change original predictions, TreeSHAP or saved scenarios. No new-patient inference/training route is exposed.
