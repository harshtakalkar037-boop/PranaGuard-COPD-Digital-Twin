-- Additive metadata only. Existing password hashes and account links are untouched.
-- Legacy pending password changes have no trustworthy issuance time and must be reissued.
ALTER TABLE portal_users ADD COLUMN temporary_password_expires_at TEXT;
ALTER TABLE portal_users ADD COLUMN temporary_password_used_at TEXT;
