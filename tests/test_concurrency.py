"""Integration test against a REAL Postgres (runs in CI and locally if DB_HOST is set).

Proves the headline claim: when many stations scan the SAME ticket at once,
exactly one is admitted.
"""
import os
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("DB_HOST"), reason="needs a real Postgres (set DB_HOST)")


def _connect():
    return psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "checkin"), user=os.environ.get("DB_USER", "checkin"),
        password=os.environ.get("DB_PASSWORD", "checkin"),
    )


@pytest.fixture
def race_ticket():
    conn = _connect()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS tickets (
        ticket_id TEXT PRIMARY KEY, attendee_name TEXT, checked_in BOOLEAN DEFAULT FALSE,
        checked_in_at TIMESTAMP, station_id INT)""")
    cur.execute("DELETE FROM tickets WHERE ticket_id = 'RACE-1'")
    cur.execute("INSERT INTO tickets (ticket_id, attendee_name) VALUES ('RACE-1', 'Race Test')")
    yield
    cur.execute("DELETE FROM tickets WHERE ticket_id = 'RACE-1'")
    conn.close()


def test_only_one_station_admits_the_same_ticket(race_ticket):
    import app as app_module

    def scan(i):
        client = app_module.app.test_client()
        return client.post("/scan", json={"ticket_id": "RACE-1", "station_id": i % 6 + 1}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(scan, range(100)))

    assert codes.count(200) == 1, "exactly one scan must be admitted"
    assert codes.count(409) == 99, "every other scan must be rejected as already used"
