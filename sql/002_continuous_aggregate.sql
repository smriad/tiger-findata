-- Daily OHLCV continuous aggregate (run after ticks are flowing)

CREATE MATERIALIZED VIEW IF NOT EXISTS one_day_candle
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    FIRST(price, time) AS "open",
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS "close",
    LAST(day_volume, time) AS day_volume
FROM crypto_ticks
GROUP BY bucket, symbol;

SELECT add_continuous_aggregate_policy(
    'one_day_candle',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);
