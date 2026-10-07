import os
from contextlib import contextmanager

from flask import Flask, jsonify, request
from psycopg2 import pool

app = Flask(__name__)

# Config comes from environment variables so the SAME image runs on the
# "legacy" EC2 box (talking to local Postgres) and in the cloud (talking to RDS).
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "checkin"),
    "user": os.environ.get("DB_USER", "checkin"),
    "password": os.environ.get("DB_PASSWORD", "checkin"),
}

# A connection pool reuses DB connections instead of opening a new one per scan.
db_pool = pool.ThreadedConnectionPool(minconn=1, maxconn=int(os.environ.get("DB_POOL_MAX", "5")), **DB_CONFIG)


@contextmanager
def get_conn():
    conn = db_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)


@app.get("/health")
def health():
    # Used by the load balancer. Deliberately does NOT touch the database,
    # so a slow DB doesn't make the ALB kill healthy containers.
    return jsonify(status="ok")


@app.get("/health/db")
def health_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
    return jsonify(status="ok", db="reachable")


@app.post("/scan")
def scan():
    body = request.get_json(silent=True) or {}
    ticket_id = body.get("ticket_id")
    station_id = body.get("station_id")
    if not ticket_id or station_id is None:
        return jsonify(result="bad_request", message="ticket_id and station_id required"), 400

    with get_conn() as conn, conn.cursor() as cur:
        # ATOMIC check-in: the check ("not yet checked in") and the write happen
        # in ONE statement. If two stations scan the same ticket at the same
        # instant, Postgres locks the row and only one UPDATE matches.
        cur.execute(
            """
            UPDATE tickets
               SET checked_in = TRUE, checked_in_at = NOW(), station_id = %s
             WHERE ticket_id = %s AND checked_in = FALSE
         RETURNING attendee_name
            """,
            (station_id, ticket_id),
        )
        row = cur.fetchone()
        if row:
            return jsonify(result="admitted", attendee=row[0]), 200

        # No row updated: either the ticket doesn't exist or it was already used.
        cur.execute("SELECT checked_in_at, station_id FROM tickets WHERE ticket_id = %s", (ticket_id,))
        existing = cur.fetchone()
        if existing is None:
            return jsonify(result="invalid", message="Ticket not found"), 404
        return jsonify(
            result="already_used",
            checked_in_at=existing[0].isoformat() if existing[0] else None,
            station_id=existing[1],
        ), 409


@app.get("/stats")
def stats():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE checked_in) FROM tickets")
        total, checked_in = cur.fetchone()
    return jsonify(total=total, checked_in=checked_in, remaining=total - checked_in)
