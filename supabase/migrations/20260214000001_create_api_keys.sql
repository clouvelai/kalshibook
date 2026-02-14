-- API keys for authenticated access to KalshiBook API.
-- Keys are SHA-256 hashed; raw key shown once at creation.
-- References auth.users for Supabase-managed user accounts.

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,  -- first 7 chars for display: "kb-abc..."
    name TEXT NOT NULL DEFAULT 'Default',
    rate_limit INT NOT NULL DEFAULT 100,  -- requests per minute
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_hash ON api_keys (key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_user ON api_keys (user_id);
