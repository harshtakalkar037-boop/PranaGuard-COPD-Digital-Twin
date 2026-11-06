# Implemented architecture

Separate editable architecture deliverables: [PPTX](architecture/PranaGuard_Architecture.pptx), [PDF](architecture/PranaGuard_Architecture.pdf), [SVG](architecture/PranaGuard_Architecture.svg).

## Runtime paths
1. The offline cohort and raw environmental caches are generated/fetched by scripts. No EHR, wearable vendor or live pollution integration is claimed.
2. `TwinEngine` loads the cohort, checks schema/ranges/duplicate patient-hours/timestamp alignment and builds causal trailing-window features.
3. A fixed first-72h median calibrates each patient's baseline. Runtime predictions start after calibration.
4. Every replay step uses the next hourly observation for all 120 twins, calls the three fitted/calibrated horizon models in a batch, and creates a new immutable version per patient.
5. SQLite atomically persists states, the replay cursor and new alerts. There is at most one unresolved alert per patient. Prior state versions remain queryable.
6. Explainability is computed on demand from a saved feature vector using native LightGBM TreeSHAP. Contributions explain raw tree log-odds, not calibrated probabilities; 72h calibration reverses raw-score direction in this run.
7. What-if requests copy the observed past up to the selected current state, never future rows. Baseline and assumption branches recompute all causal features and infer projected risk. Results are saved to a separate scenarios table; the source state is never updated.
8. FastAPI REST endpoints expose the state, predictions, explanations, scenarios, alerts, interventions, evaluation and status. A WebSocket broadcasts invalidation events; the browser reloads actual API data. A 15s REST fallback is present.
9. Vite proxies relative browser `/api` requests (including WebSockets) to FastAPI. Browser code does not call a sandbox-local backend host. Both development servers bind `0.0.0.0`; Vite permits the preview host.

The diagram's main logical chain includes all capabilities, with dashed branch arrows for direct twin-to-scenario input, prediction-to-persistence and API-triggered explanation/simulation. SQLite is cross-cutting rather than a once-only end-stage. This is a data-driven stateful research twin, not a validated mechanistic lung model or a closed-loop treatment controller.

## Modules
| Path | Responsibility |
|---|---|
| `backend/app/validation.py` | Ingestion ranges, missingness policy, timestamp and duplication checks |
| `backend/app/features.py` | Shared training/replay/scenario causal features |
| `backend/app/ml.py` | Fitted pipelines, Platt probabilities, native TreeSHAP and documented fallback |
| `backend/app/engine.py` | State transition, replay, inference, simulation, provenance |
| `backend/app/store.py` | SQLite schema, transactions, query methods |
| `backend/app/main.py` | Pydantic API validation, REST routes, WebSocket, replay task |
| `scripts/generate_data.py` | Seeded synthetic longitudinal cohort |
| `scripts/train.py` | Baseline, ablations, calibration, actual evaluation and artifacts |
| `frontend/src/` | React/TypeScript clinician dashboard, Recharts plots, all primary controls |

## Persistence model
`patients(patient_id, profile)`, `states(patient_id, version, hour, timestamp, state)`, `alerts`, `interventions`, `scenarios`, `meta`. Primary key `(patient_id, version)` ensures version uniqueness. SQLite foreign keys and WAL are enabled. Replay updates commit as one transaction; exceptions roll back. A process-local re-entrant lock serializes mutation workflows. Use **one backend worker**: distributed replay/multi-worker coordination is not implemented.

A reset is intentionally destructive for the synthetic demo (confirmed in the frontend), recreating 24 hours of persisted history and deleting alerts/actions/scenarios. It is not a production retention workflow. Interventions are append-only within a demo run; alert status may move to acknowledged or resolved but cannot reopen a resolved record. A later high-risk version can create a new alert.
