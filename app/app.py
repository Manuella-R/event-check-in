import os
import threading
import time
from contextlib import contextmanager

from flask import Flask, Response, g, jsonify, request
from prometheus_client import (CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry,
                               Counter, Histogram, generate_latest, multiprocess)
from psycopg2 import pool

app = Flask(__name__)

# ---------------------------------------------------------------- config
# Everything comes from environment variables, so the SAME image runs locally,
# behind nginx, on Render, or (in the AWS design) on ECS pointing at RDS.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "checkin"),
    "user": os.environ.get("DB_USER", "checkin"),
    "password": os.environ.get("DB_PASSWORD", "checkin"),
    # Managed databases (Render, RDS) often require TLS: set DB_SSLMODE=require.
    "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
}

# The pool is created lazily on first use, so the app can start even if the
# database is still booting, and tests can import the module without a database.
_pool = None
_pool_lock = threading.Lock()


def get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pool.ThreadedConnectionPool(
                    1, int(os.environ.get("DB_POOL_MAX", "5")), **DB_CONFIG)
    return _pool


@contextmanager
def get_conn():
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


# ---------------------------------------------------------------- metrics
REQUESTS = Counter("checkin_requests_total", "HTTP requests", ["endpoint", "status"])
LATENCY = Histogram("checkin_request_seconds", "HTTP request latency", ["endpoint"],
                    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
SCANS = Counter("checkin_scan_results_total", "Scan outcomes", ["result"])


@app.before_request
def _start_timer():
    g.t0 = time.perf_counter()


@app.after_request
def _record_metrics(resp):
    endpoint = request.endpoint or "unknown"
    if endpoint != "metrics":
        REQUESTS.labels(endpoint, str(resp.status_code)).inc()
        t0 = getattr(g, "t0", None)
        if t0 is not None:
            LATENCY.labels(endpoint).observe(time.perf_counter() - t0)
    return resp


@app.get("/metrics")
def metrics():
    # gunicorn runs several worker processes; multiprocess mode merges their metrics.
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    return Response(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    # For load balancers. Deliberately does NOT touch the database, so a slow DB
    # doesn't make the balancer kill otherwise-healthy containers.
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
        # ATOMIC check-in: the "is it unused?" check and the write happen in ONE
        # statement. If two stations scan the same ticket at the same instant,
        # Postgres locks the row and only one UPDATE matches.
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
            SCANS.labels("admitted").inc()
            return jsonify(result="admitted", attendee=row[0]), 200

        # Nothing updated: either the ticket doesn't exist or it was already used.
        cur.execute("SELECT checked_in_at, station_id FROM tickets WHERE ticket_id = %s", (ticket_id,))
        existing = cur.fetchone()
        if existing is None:
            SCANS.labels("invalid").inc()
            return jsonify(result="invalid", message="Ticket not found"), 404
        SCANS.labels("already_used").inc()
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
