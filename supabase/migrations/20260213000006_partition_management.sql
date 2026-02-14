-- Function to create future partitions for deltas (daily) and snapshots (monthly)
CREATE OR REPLACE FUNCTION create_future_partitions(days_ahead INT DEFAULT 7, months_ahead INT DEFAULT 3)
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
    i INT;
BEGIN
    -- Create daily delta partitions
    FOR i IN 0..days_ahead LOOP
        partition_date := CURRENT_DATE + i;
        partition_name := 'deltas_' || to_char(partition_date, 'YYYY_MM_DD');
        start_date := to_char(partition_date, 'YYYY-MM-DD');
        end_date := to_char(partition_date + 1, 'YYYY-MM-DD');

        BEGIN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF deltas FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        EXCEPTION WHEN duplicate_table THEN
            -- Partition already exists, skip
            NULL;
        END;
    END LOOP;

    -- Create monthly snapshot partitions
    FOR i IN 0..months_ahead LOOP
        partition_date := date_trunc('month', CURRENT_DATE) + (i || ' months')::interval;
        partition_name := 'snapshots_' || to_char(partition_date, 'YYYY_MM');
        start_date := to_char(partition_date, 'YYYY-MM-DD');
        end_date := to_char(partition_date + '1 month'::interval, 'YYYY-MM-DD');

        BEGIN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF snapshots FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        EXCEPTION WHEN duplicate_table THEN
            NULL;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
