"""Fast unit tests: no database needed (the DB layer is faked)."""
from datetime import datetime

import pytest

import app as app_module


class FakeCursor:
    def __init__(self, fetch_results):
        self.results = list(fetch_results)

    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return self.results.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def client():
    return app_module.app.test_client()


def use_fake_db(monkeypatch, fetch_results):
    cur = FakeCursor(fetch_results)
    monkeypatch.setattr(app_module, "get_conn", lambda: FakeConn(cur))


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_scan_admitted(client, monkeypatch):
    use_fake_db(monkeypatch, [("Attendee 1",)])
    r = client.post("/scan", json={"ticket_id": "T00001", "station_id": 1})
    assert r.status_code == 200 and r.get_json()["result"] == "admitted"


def test_scan_already_used(client, monkeypatch):
    use_fake_db(monkeypatch, [None, (datetime(2026, 1, 1, 9, 0), 2)])
    r = client.post("/scan", json={"ticket_id": "T00001", "station_id": 1})
    assert r.status_code == 409 and r.get_json()["station_id"] == 2


def test_scan_invalid_ticket(client, monkeypatch):
    use_fake_db(monkeypatch, [None, None])
    r = client.post("/scan", json={"ticket_id": "NOPE", "station_id": 1})
    assert r.status_code == 404


def test_scan_bad_request(client):
    assert client.post("/scan", json={}).status_code == 400


def test_metrics_exposed(client):
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200 and b"checkin_requests_total" in r.data
