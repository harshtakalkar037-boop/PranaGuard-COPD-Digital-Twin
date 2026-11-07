-- Preserve all cached values and attempt history while adding bounded retry state.
ALTER TABLE environment_attempts ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0;
ALTER TABLE environment_attempts ADD COLUMN next_retry_at TEXT;
