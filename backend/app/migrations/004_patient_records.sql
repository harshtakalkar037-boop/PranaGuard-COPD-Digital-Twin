-- Additive patient-record schema for the doctor/patient dashboards. No existing table or row is altered or deleted.
CREATE TABLE IF NOT EXISTS daily_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    entry_date TEXT NOT NULL,               -- ISO calendar date (patient-local day they report for)
    water_ml INTEGER CHECK(water_ml IS NULL OR (water_ml>=0 AND water_ml<=12000)),
    food_notes TEXT,
    activity_minutes INTEGER CHECK(activity_minutes IS NULL OR (activity_minutes>=0 AND activity_minutes<=1440)),
    sleep_hours REAL CHECK(sleep_hours IS NULL OR (sleep_hours>=0 AND sleep_hours<=24)),
    sleep_quality TEXT CHECK(sleep_quality IS NULL OR sleep_quality IN ('poor','fair','good')),
    wellbeing TEXT CHECK(wellbeing IS NULL OR wellbeing IN ('worse','same','better')),
    notes TEXT,
    edited INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,               -- patient demo username (self-service entries)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    review_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_daily_logs_patient ON daily_logs(patient_id, entry_date DESC);
-- Medication the clinician has documented for this patient. Patients never write here.
CREATE TABLE IF NOT EXISTS plan_medications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    name TEXT NOT NULL,
    dose TEXT,
    frequency TEXT,
    added_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retired INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_plan_meds ON plan_medications(patient_id);
CREATE TABLE IF NOT EXISTS med_adherence(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    medication_id INTEGER NOT NULL REFERENCES plan_medications(id),
    as_prescribed INTEGER NOT NULL CHECK(as_prescribed IN (0,1)),
    taken_at TEXT NOT NULL,
    missed_reason TEXT,
    note TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_med_adherence ON med_adherence(patient_id, taken_at DESC);
CREATE TABLE IF NOT EXISTS documents(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK(doc_type IN ('prescription','lab_report','imaging','discharge_summary','action_plan','other')),
    doc_date TEXT,
    notes TEXT,
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    data BLOB NOT NULL,
    uploaded_by TEXT NOT NULL REFERENCES care_users(username),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents ON documents(patient_id, created_at DESC);
CREATE TABLE IF NOT EXISTS follow_ups(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    doctor TEXT NOT NULL REFERENCES care_users(username),
    instructions TEXT NOT NULL,
    due_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('scheduled','completed','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    completed_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_follow_ups ON follow_ups(patient_id, due_at);
-- Uniform audit trail: every important workflow action, before/after snapshots as JSON.
CREATE TABLE IF NOT EXISTS audit_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT,
    patient_id TEXT,
    before_json TEXT,
    after_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit ON audit_events(patient_id, created_at DESC);
