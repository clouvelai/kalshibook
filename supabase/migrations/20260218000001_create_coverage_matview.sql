-- Migration: Create coverage materialized view
--
-- Pre-computes per-market coverage segments using the gaps-and-islands SQL
-- pattern. Each segment is a contiguous run of days with data from snapshots,
-- deltas, or trades. Gaps > 1 day start a new segment.

CREATE MATERIALIZED VIEW market_coverage_stats AS
WITH data_dates AS (
    -- Union all distinct dates from each data source per market
    SELECT market_ticker, captured_at::date AS data_date FROM snapshots
    UNION ALL
    SELECT market_ticker, ts::date AS data_date FROM deltas
    UNION ALL
    SELECT market_ticker, ts::date AS data_date FROM trades
),
distinct_dates AS (
    SELECT DISTINCT market_ticker, data_date
    FROM data_dates
),
with_boundaries AS (
    SELECT
        market_ticker,
        data_date,
        CASE
            WHEN data_date - LAG(data_date) OVER (
                PARTITION BY market_ticker ORDER BY data_date
            ) > 1
            THEN 1
            ELSE 0
        END AS is_boundary
    FROM distinct_dates
),
with_segments AS (
    SELECT
        market_ticker,
        data_date,
        SUM(is_boundary) OVER (
            PARTITION BY market_ticker ORDER BY data_date
        ) AS segment_id
    FROM with_boundaries
),
segments AS (
    SELECT
        market_ticker,
        segment_id::int,
        MIN(data_date) AS segment_start,
        MAX(data_date) AS segment_end,
        COUNT(*) AS days_covered
    FROM with_segments
    GROUP BY market_ticker, segment_id
)
SELECT
    s.market_ticker,
    s.segment_id,
    s.segment_start,
    s.segment_end,
    s.days_covered::int,
    (SELECT COUNT(*) FROM snapshots
     WHERE market_ticker = s.market_ticker
       AND captured_at::date >= s.segment_start
       AND captured_at::date <= s.segment_end)::int AS snapshot_count,
    (SELECT COUNT(*) FROM deltas
     WHERE market_ticker = s.market_ticker
       AND ts::date >= s.segment_start
       AND ts::date <= s.segment_end)::int AS delta_count,
    (SELECT COUNT(*) FROM trades
     WHERE market_ticker = s.market_ticker
       AND ts::date >= s.segment_start
       AND ts::date <= s.segment_end)::int AS trade_count
FROM segments s
WITH DATA;

-- Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX idx_coverage_stats_pk
    ON market_coverage_stats (market_ticker, segment_id);

-- Secondary index for fast ticker lookups
CREATE INDEX idx_coverage_stats_ticker
    ON market_coverage_stats (market_ticker);

-- Refresh function with advisory lock to prevent concurrent refresh conflicts
CREATE OR REPLACE FUNCTION refresh_coverage_stats()
RETURNS void AS $$
BEGIN
    -- Advisory lock prevents concurrent refresh attempts
    IF NOT pg_try_advisory_lock(hashtext('refresh_coverage_stats')) THEN
        RAISE NOTICE 'Coverage stats refresh already in progress, skipping';
        RETURN;
    END IF;
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY market_coverage_stats;
    EXCEPTION WHEN OTHERS THEN
        PERFORM pg_advisory_unlock(hashtext('refresh_coverage_stats'));
        RAISE;
    END;
    PERFORM pg_advisory_unlock(hashtext('refresh_coverage_stats'));
END;
$$ LANGUAGE plpgsql;
