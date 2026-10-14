"""Stream Twelve Data websocket prices into Tiger Cloud (crypto_ticks hypertable)."""

import os
import signal
import sys
import time
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from twelvedata import TDClient

load_dotenv()

DB_TABLE = "crypto_ticks"
DB_COLUMNS = ["time", "symbol", "price", "day_volume"]
MAX_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
HEARTBEAT_SECONDS = int(os.getenv("HEARTBEAT_SECONDS", "10"))


class WebsocketPipeline:
    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.conn = conn
        self.current_batch: list[tuple] = []
        self.insert_counter = 0
        self._running = True

    def flush(self) -> None:
        if not self.current_batch:
            return
        with self.conn.cursor() as cursor:
            sql = f"""
                INSERT INTO {DB_TABLE} ({",".join(DB_COLUMNS)})
                VALUES %s;
            """
            execute_values(cursor, sql, self.current_batch)
        self.conn.commit()
        self.insert_counter += 1
        print(f"Batch insert #{self.insert_counter} ({len(self.current_batch)} rows)")
        self.current_batch = []

    def _insert_values(self, data: list[tuple]) -> None:
        with self.conn.cursor() as cursor:
            sql = f"""
                INSERT INTO {DB_TABLE} ({",".join(DB_COLUMNS)})
                VALUES %s;
            """
            execute_values(cursor, sql, data)
        self.conn.commit()

    def _on_event(self, event: dict) -> None:
        if not self._running or event.get("event") != "price":
            return

        ts = event.get("timestamp")
        if ts is None:
            return

        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
        row = (
            timestamp,
            event["symbol"],
            event["price"],
            event.get("day_volume"),
        )
        self.current_batch.append(row)
        print(f"Current batch size: {len(self.current_batch)}")

        if len(self.current_batch) >= MAX_BATCH_SIZE:
            batch = self.current_batch
            self.current_batch = []
            self._insert_values(batch)
            self.insert_counter += 1
            print(f"Batch insert #{self.insert_counter}")

    def start(self, symbols: list[str], api_key: str) -> None:
        td = TDClient(apikey=api_key)
        ws = td.websocket(on_event=self._on_event)
        ws.subscribe(symbols)
        ws.connect()
        print(f"Subscribed to {symbols}. Waiting for price events…")

        while self._running:
            ws.heartbeat()
            time.sleep(HEARTBEAT_SECONDS)

    def stop(self) -> None:
        self._running = False
        self.flush()


def parse_symbols(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    symbols = parse_symbols(os.getenv("SYMBOLS", "BTC/USD,ETH/USD"))

    if not database_url:
        print("Set DATABASE_URL (see .env.example).", file=sys.stderr)
        return 1
    if not api_key:
        print("Set TWELVE_DATA_API_KEY from https://twelvedata.com/account/api-keys", file=sys.stderr)
        return 1
    if not symbols:
        print("Set SYMBOLS to at least one ticker or crypto pair.", file=sys.stderr)
        return 1

    conn = psycopg2.connect(database_url)
    pipeline = WebsocketPipeline(conn)

    def shutdown(_signum, _frame) -> None:
        print("\nShutting down, flushing batch…")
        pipeline.stop()
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        pipeline.start(symbols=symbols, api_key=api_key)
    finally:
        pipeline.stop()
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
