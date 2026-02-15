-- Settlements table with denormalized result/value columns
-- No FK to markets for same performance reasoning as deltas
CREATE TABLE IF NOT EXISTS settlements (
    market_ticker TEXT PRIMARY KEY,
    event_ticker TEXT,
    result TEXT CHECK (result IN ('yes', 'no', 'all_no', 'all_yes', 'void')),
    settlement_value INT,
    determined_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ,
    source TEXT DEFAULT 'lifecycle',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_settlements_event ON settlements (event_ticker);
CREATE INDEX IF NOT EXISTS idx_settlements_result ON settlements (result);
