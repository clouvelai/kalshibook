-- Add key_type column to api_keys for dashboard display.
-- Types are cosmetic labels (dev/prod) — no functional rate limit differences yet.

ALTER TABLE api_keys
ADD COLUMN key_type TEXT NOT NULL DEFAULT 'dev'
CHECK (key_type IN ('dev', 'prod'));
