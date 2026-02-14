-- Track markets that couldn't be subscribed due to 1k cap
CREATE TABLE IF NOT EXISTS subscription_overflow (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    market_ticker TEXT NOT NULL,
    event_ticker TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason TEXT NOT NULL DEFAULT 'cap_reached',
    resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_overflow_unresolved ON subscription_overflow (resolved) WHERE resolved = false;
