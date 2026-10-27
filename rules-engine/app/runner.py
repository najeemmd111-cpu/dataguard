"""Run every rule of one or all contracts and store the results in dq.runs / dq.results."""

from __future__ import annotations

import json
import logging
import urllib.request

import psycopg
from psycopg.types.json import Jsonb

from .checks import CHECKERS, CheckResult
from .config import get_settings
from .contracts import load_contracts, merge_custom_rules
from .db import connect
from .models import Contract

log = logging.getLogger("dataguard.runner")


def current_contracts() -> dict[str, Contract]:
    settings = get_settings()
    contracts = load_contracts(settings.contracts_dir)
    with connect() as conn:
        rows = conn.execute("SELECT dataset, rule FROM dq.custom_rules ORDER BY id").fetchall()
    return merge_custom_rules(contracts, rows)


def _run_one_rule(conn: psycopg.Connection, contract: Contract, rule, sample_size: int) -> CheckResult:
    checker = CHECKERS[rule.type]
    try:
        with conn.transaction():  # a failing query must not poison the whole run
            return checker(conn, contract, rule, sample_size)
    except psycopg.Error as exc:
        return CheckResult(False, "error", "-", f"check could not run: {exc.__class__.__name__}: {exc}".strip())


def run_checks(dataset: str | None = None, trigger: str = "manual") -> dict:
    settings = get_settings()
    contracts = current_contracts()
    if dataset is not None:
        if dataset not in contracts:
            raise KeyError(dataset)
        contracts = {dataset: contracts[dataset]}

    failures: list[dict] = []
    with connect(autocommit=True) as conn:
        run_id = conn.execute(
            "INSERT INTO dq.runs (trigger, dataset) VALUES (%s, %s) RETURNING run_id", (trigger, dataset)
        ).fetchone()[0]
        total = failed = 0
        try:
            for contract in contracts.values():
                for rule in contract.rules:
                    result = _run_one_rule(conn, contract, rule, settings.sample_size)
                    total += 1
                    result_id = conn.execute(
                        "INSERT INTO dq.results (run_id, dataset, rule_id, rule_type, severity, passed, "
                        "measured_value, threshold, message, sample_rows) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING result_id",
                        (run_id, contract.dataset, rule.id, rule.type, rule.severity, result.passed,
                         result.measured_value, result.threshold, result.message, Jsonb(result.sample_rows)),
                    ).fetchone()[0]
                    if not result.passed:
                        failed += 1
                        failures.append({"result_id": result_id, "dataset": contract.dataset, "rule_id": rule.id,
                                         "severity": rule.severity, "message": result.message,
                                         "owner": contract.owner})
            status = "failed" if failed else "passed"
        except Exception:
            status = "error"
            raise
        finally:
            conn.execute(
                "UPDATE dq.runs SET finished_at = now(), status = %s, total_rules = %s, failed_rules = %s "
                "WHERE run_id = %s",
                (status, total, failed, run_id),
            )

    _notify(run_id, failures)
    log.info("run %s: %s rules, %s failed", run_id, total, failed)
    return {"run_id": run_id, "status": status, "total_rules": total, "failed_rules": failed}


def _notify(run_id: int, failures: list[dict]) -> None:
    """Phase 4: POST failures to the n8n webhook. Never breaks a run."""
    url = get_settings().failure_webhook_url
    if not url or not failures:
        return
    body = json.dumps({"run_id": run_id, "failures": failures}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=5).close()
    except Exception as exc:  # noqa: BLE001 - alerting is best effort
        log.warning("failure webhook call failed: %s", exc)
