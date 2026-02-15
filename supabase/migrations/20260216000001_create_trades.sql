-- Trades table (HIGH volume, partitioned by day like deltas)
-- No FK on market_ticker for write performance
CREATE TABLE IF NOT EXISTS trades (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    trade_id TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    yes_price INT NOT NULL,
    no_price INT NOT NULL,
    count INT NOT NULL,
    taker_side TEXT NOT NULL CHECK (taker_side IN ('yes', 'no')),
    ts TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ts, id)
) PARTITION BY RANGE (ts);

CREATE INDEX IF NOT EXISTS idx_trades_ticker_ts ON trades (market_ticker, ts);
CREATE INDEX IF NOT EXISTS idx_trades_trade_id ON trades (trade_id);

-- Create initial daily partitions (today + next 7 days)
CREATE TABLE IF NOT EXISTS trades_2026_02_16 PARTITION OF trades
    FOR VALUES FROM ('2026-02-16') TO ('2026-02-17');
CREATE TABLE IF NOT EXISTS trades_2026_02_17 PARTITION OF trades
    FOR VALUES FROM ('2026-02-17') TO ('2026-02-18');
CREATE TABLE IF NOT EXISTS trades_2026_02_18 PARTITION OF trades
    FOR VALUES FROM ('2026-02-18') TO ('2026-02-19');
CREATE TABLE IF NOT EXISTS trades_2026_02_19 PARTITION OF trades
    FOR VALUES FROM ('2026-02-19') TO ('2026-02-20');
CREATE TABLE IF NOT EXISTS trades_2026_02_20 PARTITION OF trades
    FOR VALUES FROM ('2026-02-20') TO ('2026-02-21');
CREATE TABLE IF NOT EXISTS trades_2026_02_21 PARTITION OF trades
    FOR VALUES FROM ('2026-02-21') TO ('2026-02-22');
CREATE TABLE IF NOT EXISTS trades_2026_02_22 PARTITION OF trades
    FOR VALUES FROM ('2026-02-22') TO ('2026-02-23');
CREATE TABLE IF NOT EXISTS trades_2026_02_23 PARTITION OF trades
    FOR VALUES FROM ('2026-02-23') TO ('2026-02-24');
