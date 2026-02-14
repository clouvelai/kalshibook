-- Markets metadata table
CREATE TABLE IF NOT EXISTS markets (
    ticker TEXT PRIMARY KEY,
    market_id TEXT,
    title TEXT,
    event_ticker TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    category TEXT,
    rules TEXT,
    strike_price NUMERIC,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_markets_status ON markets (status);
CREATE INDEX IF NOT EXISTS idx_markets_event ON markets (event_ticker);
