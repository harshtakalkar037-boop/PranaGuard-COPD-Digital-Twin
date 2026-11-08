# REST and WebSocket API

OpenAPI: `http://127.0.0.1:8000/openapi.json` · interactive docs: `http://127.0.0.1:8000/docs` (also `/docs` through Vite).

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Model and engine readiness |
| GET | `/api/overview` | Cohort summaries, patient rows and actual versioned mean-risk history |
| GET | `/api/patients?q=&risk=` | Patient search and category filtering |
| GET | `/api/patients/{id}?version=` | Latest or immutable historical twin; includes all three prediction outputs |
| GET | `/api/patients/{id}/history?limit=48` | Observations and persisted prediction history |
| GET | `/api/patients/{id}/versions` | Version ledger |
| GET | `/api/patients/{id}/explanation?horizon=72` | Real drivers, patient-relative deviations and previous-score deltas |
| POST/GET | `/api/patients/{id}/scenarios` | Calculate conditional branches / list saved results |
| GET | `/api/alerts?patient_id=` | Persisted alerts |
| PATCH | `/api/alerts/{id}` | Acknowledge or resolve; resolved records are immutable |
| POST/GET | `/api/patients/{id}/interventions` | Append/list clinician action logs |
| GET | `/api/validation` | Executed experiment metrics and chart data |
| GET | `/api/status` | Cache freshness, provenance, model checksum, persistence and safety |
| GET | `/api/replay` | Replay cursor and reproducible demo metadata |
| POST | `/api/replay/step` | Advance 1–72 hours, transactionally |
| POST | `/api/replay/start` / `/pause` | Timed replay lifecycle |
| POST | `/api/replay/reset` | Destructive deterministic reset, default 24h primed history |
| WS | `/api/ws` | Twin/alert invalidation events and ping/pong |

Scenario body: `{"pm25_change_pct":-30,"adherence":0.95,"activity_multiplier":1.0}`. Ranges: PM2.5 −80 to +100%; adherence 0–1; activity 0.5–1.5. Unknown keys, non-finite values and out-of-range inputs are rejected. A `baseline_72` value at trajectory time 72 means the 72h horizon model evaluated at projected +72h, not cumulative original 72h risk.

Step body: `{"hours":12}`. Reset body: `{"prime_hours":24}` (optional target `hour`). Alert body: `{"status":"acknowledged","note":"Synthetic review"}`. Intervention body: `{"kind":"clinical_review","note":"Reviewed synthetic case"}`.

Errors: 404 missing patient/version/alert; 409 modification of resolved alert; 422 invalid assumptions/range/unsupported horizon or replay past end; 401 missing/incorrect configured demo admin token. Server errors are not replaced by fabricated outputs.

Read-only APIs are intentionally unauthenticated for synthetic review. If `PRANAGUARD_ADMIN_TOKEN` is configured in `.env`, all write endpoints require `X-Demo-Token`. Enter it in System & data for the browser session or pass it to curl. This is a shared demo gate, not patient-grade authentication/RBAC. Do not deploy real data. The replay CLI reads its token from the shell environment; when using `.env`, export the variable before running the CLI.


## Enhanced ZIP edition

Original endpoints above remain available for the frozen historical cohort. Additive fictional registrations, device simulation/ingestion, current context, notifications/reviews, demo email tests and record-level provenance are documented in [API_ENHANCED.md](enhanced/API_ENHANCED.md). New registration profiles are separate from original model twins; no live/device/manual feature substitution or new-patient prediction is enabled. See [feature status](enhanced/FEATURE_STATUS.md) for implemented versus simulated/external/planned scope.


## Completed 48-hour improvement study (latest build)

`GET /api/model48/study` returns the actual completed study, all eight development candidates, fresh-cohort comparison/uncertainty, known historical benchmark and failed acceptance checks. It explicitly returns `candidate_active:false`, `decision:retain_original` and original active model version `pg-synthetic-v1`. Missing/inconsistent study artifacts yield503 without disabling normal inference.

This endpoint is read-only. There is no model-activation or revised patient-inference endpoint because the candidate did not beat the predeclared fresh-audit gates. Existing model/alert/cutoff/scenario responses are unchanged. See [full outcome](model-upgrade/RESULTS.md).


## v3 experimental48h API (additive, version0.4.0)

- `GET /api/model48/v3/study`: predeclared fresh240-patient synthetic audit, all6 development candidates, calibration/cutoff partitions, gates, bootstrap intervals and known original-test comparison.
- `GET /api/model48/v3/patients/PG-0071?version=25`: actual fitted v3 48h probability and exact calibration-rescaled native TreeSHAP for the selected saved replay state. Omit version for latest. Includes `model_version`, `state_version`, `hour`, replay timestamp, current computation timestamp, original stored48h probability, development-only cutoff and feature/imputation audit. `persisted=false` — no writes or alerts.
- Invalid version0 =>422; missing patient/version or new/manual/device patient =>404; absent/mismatched evidence or failed gate =>503. Unsupported baseline/current-episode/follow-up state =>200 with `prediction_supported=false`, null probability and null explanation (not a fabricated zero).
- These routes are GET-only. There is no web activation, retraining or threshold-tuning endpoint. Only trusted bundled joblib artifacts are loaded; client paths/models are never accepted.

**Compatibility:** `/api/patients/{id}`, exports, histories, original explanations, `/api/overview`, scenarios, alerts,24h/72h and `/api/validation` deliberately remain **original v1**. Do NOT use their old `risks["48"]` as a v3 prediction. The frontend's48h patient card and48h explanation fetch the new route; the prior stored value is labelled separately. V2 `/api/model48/study` remains the earlier failed-study evidence, not a claim about v3. New registrations still have no supported ML prediction, even with manual baseline values.

All physiology/outcomes synthetic; this is not clinical validation, real-device integration, personal exposure, emergency triage or an intervention recommendation. V3 is a modest same-generator improvement with low recall. See [v3 results](model-v3/RESULTS.md) and [guide](model-v3/UPGRADE_GUIDE.md).
