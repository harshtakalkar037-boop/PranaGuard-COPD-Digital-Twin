-- Additive prediction-history schema. No existing table or row is altered or deleted.
-- Captures already-computed model outputs with full provenance — raw scores are never modified.
CREATE TABLE IF NOT EXISTS prediction_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    horizon INTEGER NOT NULL CHECK(horizon IN (24,48,72)),
    model_version TEXT NOT NULL,
    risk REAL NOT NULL,                -- raw model score, exactly as produced by inference
    state_version INTEGER NOT NULL,    -- twin replay state the prediction belongs to
    input_timestamp TEXT NOT NULL,     -- timestamp of the underlying twin state
    recorded_at TEXT NOT NULL,         -- when the platform persisted this record
    data_status TEXT NOT NULL CHECK(data_status IN ('supported','outside_evaluated')),
    provenance TEXT NOT NULL,          -- JSON: pipeline identity, cohort, notes
    UNIQUE(patient_id,horizon,model_version,state_version)
);
CREATE INDEX IF NOT EXISTS idx_prediction_history ON prediction_history(patient_id, horizon, input_timestamp DESC);
