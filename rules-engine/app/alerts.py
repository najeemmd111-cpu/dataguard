"""Alerts: tell people when a rule changes state, not after every run.

A rule that has been failing for days would otherwise send an alert every
15 minutes and people would stop reading them. So only two kinds of event
are sent:

- "failing":   the rule failed now and passed (or had never run) before
- "recovered": the rule passes now and failed before

The events go as one JSON POST to FAILURE_WEBHOOK_URL (the n8n workflow).
Sending is best effort: a broken webhook never breaks a check run.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import psycopg

from .config import get_settings

log = logging.getLogger("dataguard.alerts")

EventType = Literal["failing", "recovered", "test"]


def previous_status(conn: psycopg.Connection, dataset: str, rule_id: str) -> bool | None:
    """passed/failed of the rule's latest stored result, or None if it never ran."""
    row = conn.execute(
        "SELECT passed FROM dq.results WHERE dataset = %s AND rule_id = %s "
        "ORDER BY checked_at DESC, result_id DESC LIMIT 1",
        (dataset, rule_id),
    ).fetchone()
    return None if row is None else bool(row[0])


def transition(previous: bool | None, passed: bool) -> EventType | None:
    if not passed and previous is not False:
        return "failing"
    if passed and previous is False:
        return "recovered"
    return None


def event(kind: EventType, *, dataset: str, rule_id: str, rule_type: str, severity: str, owner: str,
          message: str | None, measured_value: str | None, threshold: str | None, result_id: int) -> dict:
    base = get_settings().dashboard_url
    return {
        "type": kind,
        "dataset": dataset,
        "rule_id": rule_id,
        "rule_type": rule_type,
        "severity": severity,
        "owner": owner,
        "message": message,
        "measured_value": measured_value,
        "threshold": threshold,
        "result_id": result_id,
        "dataset_url": f"{base}/datasets/{dataset}",
    }


@dataclass
class Delivery:
    sent: bool
    events: int
    status: int | None = None
    error: str | None = None


def send(run_id: int | None, events: list[dict], still_failing: int) -> Delivery:
    settings = get_settings()
    if not events:
        return Delivery(sent=False, events=0)
    if not settings.failure_webhook_url:
        return Delivery(sent=False, events=len(events), error="FAILURE_WEBHOOK_URL is not set")
    payload = {
        "source": "dataguard",
        "run_id": run_id,
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dashboard_url": settings.dashboard_url,
        "summary": {
            "failing": sum(e["type"] == "failing" for e in events),
            "recovered": sum(e["type"] == "recovered" for e in events),
            "test": sum(e["type"] == "test" for e in events),
            "still_failing": still_failing,
        },
        "events": events,
    }
    req = urllib.request.Request(
        settings.failure_webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return Delivery(sent=True, events=len(events), status=resp.status)
    except urllib.error.HTTPError as exc:
        log.warning("alert webhook answered %s", exc.code)
        return Delivery(sent=False, events=len(events), status=exc.code, error=f"webhook answered {exc.code}")
    except Exception as exc:  # noqa: BLE001 - alerting is best effort
        log.warning("alert webhook call failed: %s", exc)
        return Delivery(sent=False, events=len(events), error=str(exc))
