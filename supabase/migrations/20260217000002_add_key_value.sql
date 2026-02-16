-- Store raw API key for reveal/copy functionality.
-- NULL for keys created before this migration.
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_value TEXT;
