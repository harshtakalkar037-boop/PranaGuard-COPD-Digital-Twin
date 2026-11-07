CREATE TABLE IF NOT EXISTS portal_login_failures (
    username_hash TEXT PRIMARY KEY,
    failure_count INTEGER NOT NULL CHECK(failure_count > 0),
    window_expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS portal_login_failure_expiry ON portal_login_failures(window_expires_at);
