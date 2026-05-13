-- One-time migration for existing databases (OnlyOffice save + preview cache bust).
-- PostgreSQL:
ALTER TABLE form_templates ADD COLUMN IF NOT EXISTS oo_key_nonce INTEGER NOT NULL DEFAULT 0;
ALTER TABLE form_templates ADD COLUMN IF NOT EXISTS file_version INTEGER NOT NULL DEFAULT 0;

-- SQLite (run only if columns are missing; SQLite has no IF NOT EXISTS on ADD COLUMN in older versions):
-- ALTER TABLE form_templates ADD COLUMN oo_key_nonce INTEGER NOT NULL DEFAULT 0;
-- ALTER TABLE form_templates ADD COLUMN file_version INTEGER NOT NULL DEFAULT 0;
