-- Additive care-workspace schema. No existing table or row is altered or deleted.
CREATE TABLE IF NOT EXISTS care_users(
    username TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('doctor','patient')),
    pass_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    patient_id TEXT REFERENCES patients(patient_id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_sessions(
    token_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL REFERENCES care_users(username),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patient_assignments(
    patient_id TEXT PRIMARY KEY REFERENCES patients(patient_id),
    doctor TEXT NOT NULL REFERENCES care_users(username),
    assigned_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_reviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    doctor TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('new','awaiting_review','under_review','follow_up_scheduled','completed','closed')),
    note TEXT NOT NULL,
    follow_up_at TEXT,
    state_version INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS care_reviews_patient ON care_reviews(patient_id,status);
CREATE INDEX IF NOT EXISTS care_reviews_followup ON care_reviews(follow_up_at);
CREATE TABLE IF NOT EXISTS care_review_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES care_reviews(id),
    created_at TEXT NOT NULL,
    event TEXT NOT NULL,
    actor TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS care_plans(
    patient_id TEXT PRIMARY KEY REFERENCES patients(patient_id),
    doctor TEXT NOT NULL,
    goals TEXT NOT NULL,
    activity_guidance TEXT NOT NULL DEFAULT '',
    adherence_support TEXT NOT NULL DEFAULT '',
    environment_notes TEXT NOT NULL DEFAULT '',
    review_date TEXT,
    status TEXT NOT NULL CHECK(status IN ('draft','active','completed','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_plan_revisions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    change_note TEXT NOT NULL DEFAULT '',
    snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sputum_entries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    occurred_at TEXT NOT NULL,
    colour TEXT NOT NULL CHECK(colour IN ('clear','white','cream','yellow','green','rust','other')),
    volume TEXT NOT NULL CHECK(volume IN ('none','scant','moderate','large')),
    consistency TEXT NOT NULL CHECK(consistency IN ('thin','thick','sticky')),
    cough INTEGER NOT NULL CHECK(cough BETWEEN 0 AND 10),
    breathlessness INTEGER NOT NULL CHECK(breathlessness BETWEEN 0 AND 10),
    note TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'patient_reported_demo',
    reviewed_at TEXT,
    reviewed_by TEXT,
    review_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sputum_entries_patient ON sputum_entries(patient_id,occurred_at);
CREATE TABLE IF NOT EXISTS attachments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    entry_id INTEGER NOT NULL REFERENCES sputum_entries(id),
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK(media_type IN ('image/png','image/jpeg','image/webp')),
    size INTEGER NOT NULL CHECK(size BETWEEN 1 AND 524288),
    sha256 TEXT NOT NULL,
    data BLOB NOT NULL,
    created_at TEXT NOT NULL
);
