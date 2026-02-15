-- Add series_ticker to markets for hierarchy linking
ALTER TABLE markets ADD COLUMN IF NOT EXISTS series_ticker TEXT;
CREATE INDEX IF NOT EXISTS idx_markets_series ON markets (series_ticker);
