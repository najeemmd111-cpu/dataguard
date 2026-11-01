"""Agent tests against real PostgreSQL + pgvector, with a scripted model instead of Ollama."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

from dataguard_agent.agent import Answer, RootCauseAgent
from dataguard_agent.agent_eval import Case, grade
from dataguard_agent.chunking import load_docs
from dataguard_agent.config import get_settings
from dataguard_agent.db_setup import setup
from dataguard_agent.llm import LLMError, LoggedLLM, Reply, ScriptedBackend, ToolCall
from dataguard_agent.models import HashingEmbedder, OverlapReranker
from dataguard_agent.search import Searcher
from dataguard_agent.store import connect, rebuild
from dataguard_agent.tools import Tools

ROOT = Path(__file__).resolve().parents[2]
DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="set TEST_DATABASE_URL to a PostgreSQL with pgvector")


@pytest.fixture(scope="module")
def env():
    """Fresh schema, seeded data, one failing run, and a docs index built with the offline embedder."""
    with psycopg.connect(DB_URL, autocommit=True) as raw:
        raw.execute("DROP SCHEMA IF EXISTS dq CASCADE")
        raw.execute("DROP TABLE IF EXISTS orders, customers, products CASCADE")
        raw.execute((ROOT / "db" / "init.sql").read_text())
    subprocess.run([sys.executable, str(ROOT / "db" / "seed.py")], check=True,
                   env={**os.environ, "DATABASE_URL": DB_URL, "RESEED": "1"})
    settings = get_settings().__class__(**{**get_settings().__dict__, "database_url": DB_URL, "max_tool_rounds": 3})
    with connect(DB_URL) as conn:
        run_id = conn.execute("INSERT INTO dq.runs (trigger, status) VALUES ('test', 'failed') RETURNING run_id")\
            .fetchone()["run_id"]
        for passed, measured in [(True, "2.0h"), (False, "50.1h"), (False, "72.4h")]:
            conn.execute(
                "INSERT INTO dq.results (run_id, dataset, rule_id, rule_type, severity, passed, measured_value, "
                "threshold, message, sample_rows) VALUES (%s, 'orders', 'orders_fresh', 'freshness', 'critical', "
                "%s, %s, '24h', 'latest updated_at is 72.4h old', %s)",
                (run_id, passed, measured, Jsonb([{"age_hours": 72.4}])),
            )
        conn.commit()
        embedder = HashingEmbedder()
        chunks = load_docs(ROOT / "docs")
        rebuild(conn, chunks, embedder.embed_documents([c.text for c in chunks]), embedder.name)
        conn.commit()
        setup(conn, settings)
        searcher = Searcher(conn, embedder, OverlapReranker())
        yield conn, settings, searcher


def make_agent(env, replies):
    conn, settings, searcher = env
    backend = ScriptedBackend(replies)
    llm = LoggedLLM(backend, conn, settings)
    return RootCauseAgent(conn, llm, Tools(conn, searcher, settings), settings), backend


def answer_json(**overrides) -> str:
    data = {
        "summary": "The sales ETL stopped, so orders are 72.4 hours old.",
        "likely_cause": "The load job is not running.",
        "evidence": ["Newest updated_at is 72.4h old against 24h allowed", "Failing in the last 2 checks"],
        "fix_steps": ["Restart the sales ETL job", "Run a catch-up load", "Re-run the orders checks"],
        "confidence": "medium",
        "sources": ["runbook-orders#orders-fresh-fails", "made-up#section"],
    }
    data.update(overrides)
    return json.dumps(data)


# --- tools and the read-only user ---------------------------------------------------

def test_setup_is_repeatable(env):
    conn, settings, _ = env
    setup(conn, settings)
    setup(conn, settings)
    assert conn.execute("SELECT count(*) AS n FROM pg_roles WHERE rolname = %s",
                        (settings.readonly_user,)).fetchone()["n"] == 1


def test_run_sql_reads_business_tables(env):
    conn, settings, searcher = env
    out = Tools(conn, searcher, settings).run_sql("SELECT count(*) AS n FROM orders")
    assert out.startswith("1 row(s)") and '"n": 10025' in out


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders",
    "SELECT 1; DROP TABLE orders",
    "UPDATE orders SET amount = '0'",
])
def test_run_sql_refuses_non_select(env, sql):
    conn, settings, searcher = env
    assert Tools(conn, searcher, settings).run_sql(sql).startswith("Refused")


def test_run_sql_blocks_writes_hidden_in_a_select(env):
    conn, settings, searcher = env
    out = Tools(conn, searcher, settings).run_sql("WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d")
    assert out.startswith("SQL error")
    assert conn.execute("SELECT count(*) AS n FROM orders").fetchone()["n"] == 10025


def test_run_sql_cannot_read_other_tables(env):
    conn, settings, searcher = env
    out = Tools(conn, searcher, settings).run_sql("SELECT * FROM dq.audit_log")
    assert "permission denied" in out


def test_run_sql_limits_rows(env):
    conn, settings, searcher = env
    out = Tools(conn, searcher, settings).run_sql("SELECT order_id FROM orders")
    assert out.startswith("20 row(s) (more not shown)")


def test_rule_history_counts_the_failing_streak(env):
    conn, settings, searcher = env
    out = Tools(conn, searcher, settings).rule_history("orders", "orders_fresh")
    assert "Failing in the 2 most recent checks" in out


def test_unknown_tool_and_missing_argument(env):
    conn, settings, searcher = env
    tools = Tools(conn, searcher, settings)
    assert tools.call("drop_everything", {}).startswith("Unknown tool")
    assert tools.call("run_sql", {}).startswith("Missing argument")


# --- the agent loop -----------------------------------------------------------------

def test_full_investigation_is_logged_and_sources_are_checked(env):
    conn, _, _ = env
    agent, backend = make_agent(env, [
        Reply("", [ToolCall("rule_history", {"dataset": "orders", "rule_id": "orders_fresh"})], 900, 20, 100),
        Reply("", [ToolCall("run_sql", {"sql": "SELECT max(updated_at) FROM orders"})], 1100, 25, 120),
        Reply("I have enough evidence.", [], 1300, 10, 90),
        Reply(answer_json(), [], 1400, 150, 400),
    ])
    record = agent.investigate("orders", "orders_fresh")

    assert record["status"] == "ok"
    assert record["tool_calls"] == 2
    assert record["input_tokens"] == 4700 and record["output_tokens"] == 205
    # the made-up section is dropped and noted; the real one is kept
    assert record["answer"]["sources"] == ["runbook-orders#orders-fresh-fails"]
    assert any(t["type"] == "unverified_sources" for t in record["trace"])
    # the failure details and pre-retrieved docs were in the first prompt
    first_prompt = backend.requests[0]["messages"][1]["content"]
    assert "72.4h" in first_prompt and "[runbook-orders#orders-fresh-fails]" in first_prompt
    # the last call asked for the structured answer schema and offered no tools
    assert backend.requests[-1]["schema"] == Answer.model_json_schema()
    assert backend.requests[-1]["tools"] is None

    row = conn.execute("SELECT * FROM dq.investigations WHERE investigation_id = %s",
                       (record["investigation_id"],)).fetchone()
    assert row["status"] == "ok" and row["answer"]["confidence"] == "medium"
    calls = conn.execute("SELECT purpose, success FROM dq.llm_calls WHERE investigation_id = %s ORDER BY call_id",
                         (record["investigation_id"],)).fetchall()
    assert [c["purpose"] for c in calls] == ["agent-step"] * 3 + ["agent-answer"]
    assert all(c["success"] for c in calls)


def test_tool_rounds_are_capped(env):
    loop = [Reply("", [ToolCall("search_docs", {"query": "stale orders"})], 10, 1, 1)] * 3
    agent, backend = make_agent(env, [*loop, Reply(answer_json(), [], 10, 10, 1)])
    record = agent.investigate("orders", "orders_fresh")
    assert record["status"] == "ok"
    assert record["tool_calls"] == 3          # max_tool_rounds = 3, then it must answer
    assert len(backend.requests) == 4


def test_invalid_answer_gets_one_retry(env):
    agent, _ = make_agent(env, [
        Reply("done", [], 10, 1, 1),
        Reply('{"summary": "missing fields"}', [], 10, 5, 1),
        Reply(answer_json(confidence="high"), [], 10, 50, 1),
    ])
    record = agent.investigate("orders", "orders_fresh")
    assert record["status"] == "ok" and record["answer"]["confidence"] == "high"
    assert [t["attempt"] for t in record["trace"] if t["type"] == "invalid_answer"] == [1]


def test_two_invalid_answers_end_in_a_recorded_error(env):
    conn, _, _ = env
    agent, _ = make_agent(env, [Reply("done", [], 1, 1, 1), Reply("not json", [], 1, 1, 1),
                                Reply("still not json", [], 1, 1, 1)])
    record = agent.investigate("orders", "orders_fresh")
    assert record["status"] == "error" and "valid answer" in record["error"]
    row = conn.execute("SELECT status, error FROM dq.investigations WHERE investigation_id = %s",
                       (record["investigation_id"],)).fetchone()
    assert row["status"] == "error"


def test_model_unavailable_is_logged_as_a_failed_call(env):
    conn, _, _ = env

    class Down(ScriptedBackend):
        def chat(self, *a, **k):
            raise LLMError("Cannot reach Ollama at http://localhost:11434")

    conn_, settings, searcher = env
    llm = LoggedLLM(Down([]), conn_, settings)
    record = RootCauseAgent(conn_, llm, Tools(conn_, searcher, settings), settings).investigate("orders", "orders_fresh")
    assert record["status"] == "error" and "Ollama" in record["error"]
    failed = conn.execute("SELECT success, error FROM dq.llm_calls WHERE investigation_id = %s",
                          (record["investigation_id"],)).fetchone()
    assert failed["success"] is False and "Ollama" in failed["error"]


# --- grading ------------------------------------------------------------------------

def test_grading():
    case = Case("orders", "orders_fresh", ["runbook-orders#orders-fresh-fails", "late-etl-jobs#"],
                [["etl", "job"], ["stopped", "72"], ["timezone"]])
    record = {"status": "ok", "tool_calls": 2, "input_tokens": 100, "output_tokens": 20, "latency_ms": 1500,
              "answer": json.loads(answer_json(sources=["late-etl-jobs#symptoms"]))}
    g = grade(case, record)
    assert g["cites_right_doc"] is True
    assert g["key_facts"] == pytest.approx(2 / 3)
    assert g["missing_facts"] == [["timezone"]]
