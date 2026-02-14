-- Track detected sequence gaps for monitoring and transparency
CREATE TABLE IF NOT EXISTS sequence_gaps (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    market_ticker TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expected_seq BIGINT NOT NULL,
    received_seq BIGINT NOT NULL,
    sid BIGINT,
    recovered BOOLEAN NOT NULL DEFAULT false,
    recovered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gaps_ticker ON sequence_gaps (market_ticker);
CREATE INDEX IF NOT EXISTS idx_gaps_unrecovered ON sequence_gaps (recovered) WHERE recovered = false;
