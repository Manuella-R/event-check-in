"""Creates the tickets table and loads fake tickets. Run once per database.
Usage: python seed.py [count]
"""
import os
import sys

import psycopg2
from psycopg2.extras import execute_values

count = int(sys.argv[1]) if len(sys.argv) > 1 else 10000

conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    port=os.environ.get("DB_PORT", "5432"),
    dbname=os.environ.get("DB_NAME", "checkin"),
    user=os.environ.get("DB_USER", "checkin"),
    password=os.environ.get("DB_PASSWORD", "checkin"),
)
with conn, conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id     TEXT PRIMARY KEY,
            attendee_name TEXT,
            checked_in    BOOLEAN DEFAULT FALSE,
            checked_in_at TIMESTAMP,
            station_id    INT
        )
    """)
    rows = [(f"T{i:05d}", f"Attendee {i}") for i in range(1, count + 1)]
    execute_values(
        cur,
        "INSERT INTO tickets (ticket_id, attendee_name) VALUES %s ON CONFLICT DO NOTHING",
        rows,
    )
print(f"Seeded {count} tickets")
