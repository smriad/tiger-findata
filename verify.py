"""Quick check that crypto_ticks is receiving data."""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Set DATABASE_URL", file=sys.stderr)
        return 1

    with psycopg2.connect(url) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, count(*) AS ticks, max(time) AS latest
            FROM crypto_ticks
            GROUP BY symbol
            ORDER BY symbol;
            """
        )
        rows = cur.fetchall()
        if not rows:
            print("No rows in crypto_ticks yet. Run ingest.py and wait for a batch flush.")
            return 0
        for symbol, count, latest in rows:
            print(f"{symbol}: {count} ticks (latest {latest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
