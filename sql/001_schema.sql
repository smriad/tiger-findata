-- Tiger Cloud financial tick pipeline schema
-- https://www.tigerdata.com/docs/learn/tutorials/ingest-real-time-financial-data

CREATE TABLE IF NOT EXISTS crypto_ticks (
    "time" TIMESTAMPTZ,
    symbol TEXT,
    price DOUBLE PRECISION,
    day_volume NUMERIC
) WITH (
    tsdb.hypertable,
    tsdb.segmentby = 'symbol',
    tsdb.orderby = 'time DESC'
);

CREATE TABLE IF NOT EXISTS crypto_assets (
    symbol TEXT UNIQUE,
    "name" TEXT
);

INSERT INTO crypto_assets (symbol, name) VALUES
    ('BTC/USD', 'Bitcoin'),
    ('ETH/USD', 'Ethereum'),
    ('MSFT', 'Microsoft'),
    ('AAPL', 'Apple')
ON CONFLICT (symbol) DO NOTHING;
