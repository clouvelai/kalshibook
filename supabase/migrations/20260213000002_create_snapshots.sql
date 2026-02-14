-- Orderbook snapshots (partitioned by month)
CREATE TABLE IF NOT EXISTS snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    market_ticker TEXT NOT NULL REFERENCES markets(ticker),
    captured_at TIMESTAMPTZ NOT NULL,
    seq BIGINT NOT NULL,
    yes_levels JSONB NOT NULL,
    no_levels JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'ws_subscribe',
    PRIMARY KEY (captured_at, id)
) PARTITION BY RANGE (captured_at);

CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_time ON snapshots (market_ticker, captured_at DESC);

-- Create initial monthly partitions
CREATE TABLE IF NOT EXISTS snapshots_2026_02 PARTITION OF snapshots
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS snapshots_2026_03 PARTITION OF snapshots
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS snapshots_2026_04 PARTITION OF snapshots
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
