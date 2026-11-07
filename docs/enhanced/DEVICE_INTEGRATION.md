# Device Integration — generic software simulations

## What actually exists
| Generic type | Accepted simulated metrics | Units |
|---|---|---|
| Pulse oximeter | SpO₂, heart rate | %,bpm |
| Smartwatch | Heart rate, respiratory rate, interval step count | bpm,breaths/min,steps |
| Fitness band | Heart rate, interval step count | bpm,steps |
| Portable spirometer | FEV₁,FVC | L,L |

No physical hardware, brand SDK, BLE/USB transport, validated measurement accuracy or commercial compatibility is claimed. FEV₁ litres are not converted into % predicted. Interval step counts are not a daily step total and are not summed across competing devices.

## Use the screen
Select a synthetic patient, choose a generic type, optional fictional label and interval2–300 seconds. **Associate** creates a disconnected record; it does not start generation. Each device card has an explicit **Start simulation**, **Stop simulation**, configurable interval and **Inspect readings**. Stop first to change the running interval. Status is`Connected (Simulation)`,`Disconnected`or`Error`; freshness is separate. Reading timestamps, units and provenance remain visible. Devices and history persist; active simulations intentionally stop after backend restart and create an interruption notice.

## Real ingestion path, not frontend counters
A single backend worker schedules deterministic synthetic samples based on device/run/sequence. It submits JSON through an internal HTTPX ASGI client to the **same**`POST /api/enhanced/ingestion` REST route. Pydantic validation, authorization, association, unit/range checks, event deduplication and SQLite transactions are therefore exercised. The frontend never fabricates or increments readings locally.

- `(device_id,event_id)` is unique; the normalized payload is SHA256-hashed.
- Exact retry: returns existing event/monitoring-version with`duplicate:true`; no duplicate reading/state/notification.
- Reused ID with different content:409.
- Source must be`simulated_device`; unknown metrics, wrong units, implausible values, duplicate metrics, future/naive/backdated timestamps and association mismatch are rejected.
- New observations require the simulation to be explicitly started. An exact already-accepted retry remains idempotent after stop.
- Each accepted event appends readings and a monitoring-only state. Out-of-order values cannot replace a newer current metric. Missing metric fields remain missing. No ML probability is generated or historical feature frame mutated.

## Authentication and architecture
The backend computes a per-device HMAC token from`PRANAGUARD_DEVICE_SECRET`; only its hash is stored. The internal simulator supplies`X-Device-Token`, and the optional shared`X-Demo-Token`if configured. Tokens/master secrets are never returned by the UI APIs or logged. With no configured master, ephemeral local tokens rotate on restart. At most16 active simulations and16 associations per patient are supported in this local demo.

This is an **authenticated adapter boundary**, not completed real-hardware enrollment. A future authorized transport would need approved provenance, enrollment/token provisioning/rotation, clock/rate/replay protection, consent, encrypted channels, RBAC and independent measurement validation. Do not label external hardware data as simulated to bypass missing real-device functionality. Do not copy a master secret into frontend code.

## Data-quality / monitoring demonstration rules
- SpO₂≤92% or heart rate≥110bpm can create a labelled unvalidated monitoring-rule notice, deduplicated by device/hour.
- Explicit stop, backend-restart interruption, ingestion error and stale enabled streams create data-quality notices.
- Stale stream rule: no ingestion for more than max(30s,3×configured interval) while enabled.

These are software-test/demo thresholds, not established COPD clinical cutoffs, urgent actions or emergency response. The original historical model alert remains separate.

## Verification
Backend tests exercise actual REST ingestion and internal simulator routing, authentication, validation, duplicate/conflicting events, first72h gates, restart/stale/error handling and unchanged original twins. Chromium ran all four generic simulators, checked actual ingested rows, stopped them, checked that new rows ceased, rendered the saved trend and selected prior monitoring versions. See`VERIFICATION.md`and the machine-readable reports.
