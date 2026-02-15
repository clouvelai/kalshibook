-- Series table (top-level grouping for related events)
CREATE TABLE IF NOT EXISTS series (
    ticker TEXT PRIMARY KEY,
    title TEXT,
    frequency TEXT,
    category TEXT,
    tags TEXT[],
    settlement_sources JSONB,
    metadata JSONB,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Events table (groups markets within a series)
CREATE TABLE IF NOT EXISTS events (
    event_ticker TEXT PRIMARY KEY,
    series_ticker TEXT,
    title TEXT,
    sub_title TEXT,
    category TEXT,
    mutually_exclusive BOOLEAN,
    status TEXT,
    strike_date TIMESTAMPTZ,
    strike_period TEXT,
    metadata JSONB,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_series ON events (series_ticker);
CREATE INDEX IF NOT EXISTS idx_events_status ON events (status);
CREATE INDEX IF NOT EXISTS idx_events_category ON events (category);
