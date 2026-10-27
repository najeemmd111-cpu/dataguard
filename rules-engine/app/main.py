"""DataGuard rules engine API."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .config import get_settings
from .contracts import ContractError, parse_rule
from .db import connect, fetch_all, fetch_one
from .runner import current_contracts, run_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dataguard.api")


async def wait_for_database(attempts: int = 30, delay: float = 1.0) -> None:
    """Retry until Postgres answers. Container DNS and the DB can lag a few seconds behind startup."""
    for attempt in range(1, attempts + 1):
        try:
            with connect() as conn:
                conn.execute("SELECT 1")
            if attempt > 1:
                log.info("database reachable after %s attempts", attempt)
            return
        except psycopg.OperationalError as exc:
            if attempt == attempts:
                raise
            log.warning("database not reachable yet (%s/%s): %s", attempt, attempts, exc)
            await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_database()
    scheduler = None
    if get_settings().scheduler_enabled:
        from .scheduler import start_scheduler
        scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="DataGuard rules engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

Severity = Literal["low", "medium", "high", "critical"]


class RunRequest(BaseModel):
    dataset: str | None = None


class NewRule(BaseModel):
    dataset: str
    rule: dict
    created_by: str = "api"


class NewAnnotation(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
    author: str = "api"


@app.get("/health")
def health() -> dict:
    with connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/runs", status_code=201)
def create_run(body: RunRequest | None = None) -> dict:
    try:
        return run_checks(dataset=body.dataset if body else None, trigger="api")
    except KeyError:
        raise HTTPException(404, f"unknown dataset {body.dataset!r}")


@app.get("/runs")
def list_runs(limit: int = Query(20, ge=1, le=200)) -> list[dict]:
    return fetch_all("SELECT * FROM dq.runs ORDER BY run_id DESC LIMIT %s", (limit,))


@app.get("/runs/{run_id}")
def get_run(run_id: int) -> dict:
    run = fetch_one("SELECT * FROM dq.runs WHERE run_id = %s", (run_id,))
    if not run:
        raise HTTPException(404, "run not found")
    run["results"] = fetch_all("SELECT * FROM dq.results WHERE run_id = %s ORDER BY result_id", (run_id,))
    return run


LATEST_RESULTS = """
    SELECT DISTINCT ON (r.dataset, r.rule_id) r.*,
           COALESCE((SELECT json_agg(a ORDER BY a.created_at)
                     FROM dq.annotations a WHERE a.result_id = r.result_id), '[]') AS annotations
    FROM dq.results r
    {where}
    ORDER BY r.dataset, r.rule_id, r.checked_at DESC, r.result_id DESC
"""


def _active(rows: list[dict], contracts: dict) -> list[dict]:
    """Drop results for rules that no longer exist in the contracts."""
    live = {(name, r.id) for name, c in contracts.items() for r in c.rules}
    return [r for r in rows if (r["dataset"], r["rule_id"]) in live]


def _health(results: list[dict]) -> str:
    if not results:
        return "unknown"
    failing = {r["severity"] for r in results if not r["passed"]}
    if failing & {"critical", "high"}:
        return "red"
    return "amber" if failing else "green"


@app.get("/datasets")
def list_datasets() -> list[dict]:
    contracts = current_contracts()
    latest = _active(fetch_all(LATEST_RESULTS.format(where="")), contracts)
    out = []
    for name, c in contracts.items():
        rows = [r for r in latest if r["dataset"] == name]
        out.append({
            "dataset": name, "table": c.table, "owner": c.owner, "description": c.description,
            "schedule": c.schedule, "rule_count": len(c.rules),
            "failing_rules": sum(1 for r in rows if not r["passed"]),
            "last_checked": max((r["checked_at"] for r in rows), default=None),
            "health": _health(rows),
        })
    return out


@app.get("/datasets/{name}")
def get_dataset(name: str) -> dict:
    contract = current_contracts().get(name)
    if not contract:
        raise HTTPException(404, f"unknown dataset {name!r}")
    results = _active(fetch_all(LATEST_RESULTS.format(where="WHERE r.dataset = %s"), (name,)), {name: contract})
    data = contract.model_dump(by_alias=True)
    data["latest_results"] = results
    data["health"] = _health(results)
    return data


@app.get("/failures")
def list_failures(
    severity: Severity | None = None,
    dataset: str | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    """Rules whose most recent result is a failure."""
    rows = _active(fetch_all(LATEST_RESULTS.format(where="")), current_contracts())
    rows = [r for r in rows if not r["passed"]
            and (severity is None or r["severity"] == severity)
            and (dataset is None or r["dataset"] == dataset)]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    rows.sort(key=lambda r: (order[r["severity"]], r["dataset"], r["rule_id"]))
    return rows[:limit]


@app.post("/rules", status_code=201)
def add_rule(body: NewRule) -> dict:
    contracts = current_contracts()
    contract = contracts.get(body.dataset)
    if not contract:
        raise HTTPException(404, f"unknown dataset {body.dataset!r}")
    try:
        rule = parse_rule(body.rule)
    except ContractError as exc:
        raise HTTPException(422, f"invalid rule: {exc}")
    if rule.type == "schema" and not contract.schema_:
        raise HTTPException(422, "this dataset has no schema section")
    if any(r.id == rule.id for r in contract.rules):
        raise HTTPException(409, f"rule {rule.id!r} already exists on {body.dataset}")
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO dq.custom_rules (dataset, rule, created_by) VALUES (%s, %s, %s)",
                (body.dataset, Jsonb(rule.model_dump(exclude_none=True)), body.created_by),
            )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, f"rule {rule.id!r} already exists on {body.dataset}")
    return {"dataset": body.dataset, "rule": rule.model_dump(exclude_none=True)}


@app.post("/results/{result_id}/annotations", status_code=201)
def annotate(result_id: int, body: NewAnnotation) -> dict:
    if not fetch_one("SELECT 1 FROM dq.results WHERE result_id = %s", (result_id,)):
        raise HTTPException(404, "result not found")
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO dq.annotations (result_id, note, author) VALUES (%s, %s, %s) "
            "RETURNING annotation_id, created_at",
            (result_id, body.note, body.author),
        ).fetchone()
    return {"annotation_id": row[0], "result_id": result_id, "note": body.note,
            "author": body.author, "created_at": row[1]}


@app.get("/audit")
def audit_log(limit: int = Query(100, ge=1, le=1000)) -> list[dict]:
    return fetch_all("SELECT * FROM dq.audit_log ORDER BY audit_id DESC LIMIT %s", (limit,))


@app.get("/llm-calls")
def llm_calls(limit: int = Query(200, ge=1, le=2000)) -> list[dict]:
    """Phase 3: feeds the cost and latency page."""
    return fetch_all("SELECT * FROM dq.llm_calls ORDER BY call_id DESC LIMIT %s", (limit,))
