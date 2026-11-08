-- Additive only. Existing patients/states/alerts/actions/scenarios are never rewritten.
CREATE TABLE IF NOT EXISTS registrations (
 patient_id TEXT PRIMARY KEY REFERENCES patients(patient_id),
 request_id TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL,
 created_at TEXT NOT NULL, details TEXT NOT NULL,
 source_type TEXT NOT NULL CHECK(source_type='manual_demo')
);
CREATE TABLE IF NOT EXISTS devices (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(patient_id),
 kind TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'disconnected' CHECK(status IN ('connected_simulation','disconnected','error')),
 is_simulating INTEGER NOT NULL DEFAULT 0 CHECK(is_simulating IN (0,1)),
 interval_seconds INTEGER NOT NULL DEFAULT 5 CHECK(interval_seconds BETWEEN 2 AND 300),
 last_seen_at TEXT, next_due_at TEXT, last_error TEXT,
 run_id TEXT, sequence INTEGER NOT NULL DEFAULT 0, token_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS devices_patient ON devices(patient_id,created_at);
CREATE TABLE IF NOT EXISTS ingestion_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 device_id TEXT NOT NULL REFERENCES devices(id), patient_id TEXT NOT NULL REFERENCES patients(patient_id),
 event_id TEXT NOT NULL, payload_hash TEXT NOT NULL, observed_at TEXT NOT NULL,
 received_at TEXT NOT NULL, source_type TEXT NOT NULL CHECK(source_type='simulated_device'),
 UNIQUE(device_id,event_id)
);
CREATE TABLE IF NOT EXISTS device_readings (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_pk INTEGER NOT NULL REFERENCES ingestion_events(id),
 patient_id TEXT NOT NULL REFERENCES patients(patient_id), device_id TEXT NOT NULL REFERENCES devices(id),
 metric TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
 observed_at TEXT NOT NULL, received_at TEXT NOT NULL, source_type TEXT NOT NULL DEFAULT 'simulated_device',
 UNIQUE(event_pk,metric)
);
CREATE INDEX IF NOT EXISTS readings_patient_time ON device_readings(patient_id,observed_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS readings_device_time ON device_readings(device_id,observed_at DESC);
CREATE TABLE IF NOT EXISTS monitoring_states (
 id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL REFERENCES patients(patient_id),
 event_pk INTEGER NOT NULL UNIQUE REFERENCES ingestion_events(id),
 created_at TEXT NOT NULL, snapshot TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS monitoring_patient_version ON monitoring_states(patient_id,id DESC);
CREATE TABLE IF NOT EXISTS demo_observations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL REFERENCES patients(patient_id),
 created_at TEXT NOT NULL, symptom_score INTEGER NOT NULL CHECK(symptom_score BETWEEN 0 AND 10),
 adherence REAL NOT NULL CHECK(adherence BETWEEN 0 AND 1), note TEXT NOT NULL,
 source_type TEXT NOT NULL DEFAULT 'manual_demo'
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT REFERENCES patients(patient_id),
 category TEXT NOT NULL CHECK(category IN ('patient_monitoring','environment','data_quality','system')),
 title TEXT NOT NULL, reason TEXT NOT NULL, source TEXT NOT NULL, source_type TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
 CHECK(status IN ('active','acknowledged','under_review','resolved','closed')),
 read_at TEXT, dedupe_key TEXT NOT NULL UNIQUE,
 legacy_alert_id INTEGER REFERENCES alerts(id) ON DELETE SET NULL,
 metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS notifications_filters ON notifications(patient_id,category,status,id DESC);
CREATE TABLE IF NOT EXISTS notification_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, notification_id INTEGER NOT NULL REFERENCES notifications(id),
 created_at TEXT NOT NULL, from_status TEXT, to_status TEXT NOT NULL,
 action TEXT NOT NULL, note TEXT NOT NULL, actor TEXT NOT NULL DEFAULT 'demo_workspace'
);
CREATE TABLE IF NOT EXISTS email_outbox (
 id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
 status TEXT NOT NULL, detail TEXT NOT NULL, channel TEXT NOT NULL DEFAULT 'demo_test_only'
);
CREATE TABLE IF NOT EXISTS environment_cache (
 city TEXT NOT NULL, component TEXT NOT NULL CHECK(component IN ('air','weather')),
 retrieved_at TEXT NOT NULL, valid_at TEXT NOT NULL, payload TEXT NOT NULL,
 last_attempt_at TEXT, last_error TEXT, PRIMARY KEY(city,component)
);
CREATE TABLE IF NOT EXISTS environment_attempts (
 city TEXT NOT NULL, component TEXT NOT NULL, attempted_at TEXT NOT NULL,
 error TEXT, PRIMARY KEY(city,component)
);
CREATE TABLE IF NOT EXISTS enhanced_audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, category TEXT NOT NULL,
 patient_id TEXT REFERENCES patients(patient_id), source TEXT NOT NULL, detail TEXT NOT NULL
);
