-- Per-API-key usage tracking for credit metering.
-- Records every API request with endpoint and credits charged.
-- Used for usage analytics and billing verification.

CREATE TABLE IF NOT EXISTS api_key_usage (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    credits_charged INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_api_key_usage_key_time ON api_key_usage (api_key_id, created_at DESC);
