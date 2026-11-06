CREATE TABLE IF NOT EXISTS portal_admin_audit (id INTEGER PRIMARY KEY, actor TEXT NOT NULL DEFAULT 'local_admin', action TEXT NOT NULL, username TEXT NOT NULL, patient_id TEXT REFERENCES patients(patient_id), created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS admin_audit_time ON portal_admin_audit(created_at DESC);
