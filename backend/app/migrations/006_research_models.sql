-- 006 research models (v7, additive): external research model registry, hashed inference log,
-- experiment runs/metrics and research dataset index tables. Existing tables are untouched.
CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT PRIMARY KEY,
    model_display_name TEXT NOT NULL,
    model_kind TEXT NOT NULL,
    version TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    task_type TEXT NOT NULL,
    feature_schema_json TEXT NOT NULL DEFAULT '{}',
    preprocessing_json TEXT NOT NULL DEFAULT '{}',
    artifact_path TEXT,
    inference_method TEXT NOT NULL DEFAULT 'none',
    supported_outputs_json TEXT NOT NULL DEFAULT '[]',
    evaluation_json TEXT NOT NULL DEFAULT '{}',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    provenance_evidence_class TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL REFERENCES model_registry(model_id),
    version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    input_summary_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    evidence_class TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_model_predictions_model ON model_predictions(model_id, id DESC);
CREATE TABLE IF NOT EXISTS experiment_runs (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES model_registry(model_id),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    protocol_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS research_cough_recordings (
    filename TEXT PRIMARY KEY,
    class_label TEXT NOT NULL,
    publisher_split TEXT NOT NULL,
    duration_s REAL,
    samplerate_hz INTEGER,
    channels INTEGER,
    participant_id TEXT,
    evidence_class TEXT NOT NULL DEFAULT 'REAL_OBSERVED',
    provenance_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS research_tolife_participants (
    coded_participant_id TEXT PRIMARY KEY,
    country TEXT,
    monitoring_days INTEGER,
    first_day TEXT,
    last_day TEXT,
    evidence_class TEXT NOT NULL DEFAULT 'REAL_OBSERVED',
    provenance_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS research_tolife_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coded_participant_id TEXT NOT NULL,
    event_date TEXT NOT NULL,
    severity TEXT,
    in_observed_frame INTEGER NOT NULL DEFAULT 0,
    valid_days_prior_7d INTEGER NOT NULL DEFAULT 0,
    evidence_class TEXT NOT NULL DEFAULT 'REAL_OBSERVED',
    provenance_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_research_tolife_events_pid ON research_tolife_events(coded_participant_id);
CREATE TABLE IF NOT EXISTS research_evaluation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    experiment_id TEXT,
    metric TEXT NOT NULL,
    horizon_hours INTEGER,
    value REAL,
    ci_low REAL,
    ci_high REAL,
    note TEXT,
    recorded_at TEXT NOT NULL
);
