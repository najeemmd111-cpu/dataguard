"""Alerts fire on state changes only, and a broken webhook never breaks a run."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from app.alerts import transition

pytestmark = pytest.mark.db


class Capture(BaseHTTPRequestHandler):
    received: list[dict] = []
    status = 200

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers["Content-Length"])
        Capture.received.append(json.loads(self.rfile.read(length)))
        self.send_response(Capture.status)
        self.end_headers()

    def log_message(self, *args):  # keep test output quiet
        pass


@pytest.fixture()
def webhook(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Capture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    Capture.received = []
    Capture.status = 200
    monkeypatch.setenv("FAILURE_WEBHOOK_URL", f"http://127.0.0.1:{server.server_port}/webhook/dataguard-failure")
    monkeypatch.setenv("DASHBOARD_URL", "http://dash.test")
    yield Capture
    server.shutdown()


@pytest.fixture()
def client(database_url):
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("previous, passed, expected", [
    (None, False, "failing"),     # first check ever, failing
    (True, False, "failing"),     # was passing, now failing
    (False, False, None),         # still failing: no new alert
    (False, True, "recovered"),
    (True, True, None),
    (None, True, None),
])
def test_transition(previous, passed, expected):
    assert transition(previous, passed) == expected


def test_alerts_fire_once_when_a_rule_starts_failing_and_once_when_it_recovers(client, conn, webhook):
    client.post("/runs", json={"dataset": "orders"})          # settle the current state
    webhook.received.clear()

    # Simulate the sales ETL catching up: one fresh row makes orders_fresh pass.
    row = conn.execute("SELECT id, updated_at FROM orders ORDER BY id LIMIT 1").fetchone()
    conn.execute("UPDATE orders SET updated_at = now() WHERE id = %s", (row[0],))
    conn.commit()
    try:
        run = client.post("/runs", json={"dataset": "orders"}).json()
        assert run["alerts"] == {"events": 1, "sent": True}
        payload = webhook.received[-1]
        assert payload["summary"]["recovered"] == 1
        event = payload["events"][0]
        assert event["type"] == "recovered" and event["rule_id"] == "orders_fresh"
        assert event["dataset_url"] == "http://dash.test/datasets/orders"
        assert event["owner"] == "sales-data-team"

        # Nothing changed: no alert at all.
        client.post("/runs", json={"dataset": "orders"})
        assert len(webhook.received) == 1
    finally:
        # The ETL "stops" again: the next run reports orders_fresh failing again.
        conn.execute("UPDATE orders SET updated_at = %s WHERE id = %s", (row[1], row[0]))
        conn.commit()

    run = client.post("/runs", json={"dataset": "orders"}).json()
    assert run["alerts"]["events"] == 1
    payload = webhook.received[-1]
    event = payload["events"][0]
    assert event["type"] == "failing" and event["rule_id"] == "orders_fresh" and event["severity"] == "critical"
    assert payload["summary"]["still_failing"] == 2          # orders_unique_id and orders_schema
    assert event["measured_value"].endswith("h") and event["threshold"] == "24h"


def test_a_broken_webhook_never_breaks_a_run(client, conn, monkeypatch):
    monkeypatch.setenv("FAILURE_WEBHOOK_URL", "http://127.0.0.1:9/nothing-listens-here")
    row = conn.execute("SELECT id, updated_at FROM orders ORDER BY id LIMIT 1").fetchone()
    conn.execute("UPDATE orders SET updated_at = now() WHERE id = %s", (row[0],))
    conn.commit()
    try:
        run = client.post("/runs", json={"dataset": "orders"})
        assert run.status_code == 201
        assert run.json()["alerts"] == {"events": 1, "sent": False}
    finally:
        conn.execute("UPDATE orders SET updated_at = %s WHERE id = %s", (row[1], row[0]))
        conn.commit()
        client.post("/runs", json={"dataset": "orders"})


def test_test_alert_sends_the_current_failures(client, webhook):
    client.post("/runs", json={})
    response = client.post("/alerts/test")
    assert response.status_code == 200
    assert response.json()["events"] >= 4
    payload = webhook.received[-1]
    assert {e["type"] for e in payload["events"]} == {"test"}
    assert {"orders_fresh", "customers_email_complete"} <= {e["rule_id"] for e in payload["events"]}


def test_test_alert_explains_missing_configuration(client, monkeypatch):
    monkeypatch.delenv("FAILURE_WEBHOOK_URL", raising=False)
    response = client.post("/alerts/test")
    assert response.status_code == 409
    assert "FAILURE_WEBHOOK_URL" in response.json()["detail"]
