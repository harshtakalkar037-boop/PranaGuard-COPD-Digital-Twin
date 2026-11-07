CREATE TABLE IF NOT EXISTS care_followup_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL UNIQUE REFERENCES care_reviews(id),
    patient_id TEXT NOT NULL,
    doctor TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS care_followup_patient_completed ON care_followup_completions(patient_id, completed_at);
