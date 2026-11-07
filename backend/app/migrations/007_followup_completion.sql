CREATE TABLE IF NOT EXISTS followup_completions (
    review_id INTEGER PRIMARY KEY REFERENCES doctor_reviews(id),
    doctor_id INTEGER NOT NULL REFERENCES portal_users(id),
    notes TEXT NOT NULL,
    completed_at TEXT NOT NULL
);
