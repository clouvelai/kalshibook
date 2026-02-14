-- Orderbook deltas (HIGH volume, partitioned by day)
-- No FK on market_ticker for write performance
CREATE TABLE IF NOT EXISTS deltas (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    market_ticker TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    seq BIGINT NOT NULL,
    sid BIGINT NOT NULL,
    price_cents INT NOT NULL,
    delta_amount INT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
    PRIMARY KEY (ts, id)
) PARTITION BY RANGE (ts);

CREATE INDEX IF NOT EXISTS idx_deltas_ticker_seq ON deltas (market_ticker, seq);
CREATE INDEX IF NOT EXISTS idx_deltas_ticker_ts ON deltas (market_ticker, ts);

-- Create initial daily partitions (today + next 7 days)
CREATE TABLE IF NOT EXISTS deltas_2026_02_13 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-13') TO ('2026-02-14');
CREATE TABLE IF NOT EXISTS deltas_2026_02_14 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-14') TO ('2026-02-15');
CREATE TABLE IF NOT EXISTS deltas_2026_02_15 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-15') TO ('2026-02-16');
CREATE TABLE IF NOT EXISTS deltas_2026_02_16 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-16') TO ('2026-02-17');
CREATE TABLE IF NOT EXISTS deltas_2026_02_17 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-17') TO ('2026-02-18');
CREATE TABLE IF NOT EXISTS deltas_2026_02_18 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-18') TO ('2026-02-19');
CREATE TABLE IF NOT EXISTS deltas_2026_02_19 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-19') TO ('2026-02-20');
CREATE TABLE IF NOT EXISTS deltas_2026_02_20 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-20') TO ('2026-02-21');
