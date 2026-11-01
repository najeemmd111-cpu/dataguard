"""Tools the agent can call. Each returns plain text the model can read, never raises at the model."""

from __future__ import annotations

import json
import re
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from .config import Settings
from .search import Searcher

MAX_ROWS = 20
MAX_CHARS = 1800   # keep tool results short: small models have small context windows

TABLES_HELP = (
    "public.orders(id, order_id, customer_id, product_id, quantity, amount, status, created_at, updated_at); "
    "public.customers(customer_id, email, country, created_at, updated_at); "
    "public.products(product_id, name, category, price, updated_at); "
    "dq.results(result_id, run_id, dataset, rule_id, rule_type, severity, passed, measured_value, threshold, "
    "message, checked_at)"
)

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search the DataGuard documentation (rule types, common causes, runbooks, fixes).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "What to look for, in plain words"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rule_history",
            "description": "Recent results of one rule, newest first, to see when the failure started.",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string"}, "rule_id": {"type": "string"}},
                "required": ["dataset", "rule_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Run ONE read-only PostgreSQL SELECT query (max 20 rows returned). Tables: " + TABLES_HELP,
            "parameters": {
                "type": "object",
                "properties": {"sql": {"type": "string", "description": "A single SELECT statement"}},
                "required": ["sql"],
            },
        },
    },
]

_SELECT = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


def _clip(text: str) -> str:
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + " …(truncated)"


def readonly_conninfo(settings: Settings) -> str:
    params = conninfo_to_dict(settings.database_url)
    params.update(user=settings.readonly_user, password=settings.readonly_password)
    return make_conninfo(**params)


class Tools:
    def __init__(self, conn: psycopg.Connection, searcher: Searcher, settings: Settings):
        self.conn = conn
        self.searcher = searcher
        self.settings = settings
        self.seen_sections: dict[str, str] = {}   # section_id -> heading, for checking cited sources

    # --- the tools -----------------------------------------------------------------
    def search_docs(self, query: str, limit: int = 3) -> str:
        hits = self.searcher.search(query, method="hybrid_rerank", limit=limit)
        if not hits:
            return "No matching documentation."
        parts = []
        for h in hits:
            self.seen_sections[h.section_id] = h.heading
            body = h.text.split("\n\n", 1)[-1]
            parts.append(f"[{h.section_id}]\n{body[:700]}")
        return _clip("\n\n".join(parts))

    def rule_history(self, dataset: str, rule_id: str, limit: int = 10) -> str:
        rows = self.conn.execute(
            "SELECT checked_at, passed, measured_value, threshold FROM dq.results "
            "WHERE dataset = %s AND rule_id = %s ORDER BY checked_at DESC, result_id DESC LIMIT %s",
            (dataset, rule_id, limit),
        ).fetchall()
        if not rows:
            return f"No results found for {dataset}/{rule_id}."
        failing = 0
        for r in rows:
            if r["passed"]:
                break
            failing += 1
        lines = [f"Last {len(rows)} results (newest first). Failing in the {failing} most recent checks."]
        for r in rows:
            status = "pass" if r["passed"] else "FAIL"
            lines.append(f"{r['checked_at']:%Y-%m-%d %H:%M} {status} measured={r['measured_value']} "
                         f"allowed={r['threshold']}")
        return _clip("\n".join(lines))

    def run_sql(self, sql: str) -> str:
        query = sql.strip().rstrip(";").strip()
        if not _SELECT.match(query):
            return "Refused: only a single SELECT (or WITH … SELECT) query is allowed."
        if ";" in query:
            return "Refused: only one statement is allowed."
        try:
            # Separate login with SELECT-only grants; the session is read-only and times out after 5 s.
            with psycopg.connect(readonly_conninfo(self.settings), row_factory=dict_row, autocommit=False) as ro:
                ro.read_only = True
                ro.execute("SET statement_timeout = '5s'")
                rows = ro.execute(f"SELECT * FROM ({query}) AS agent_query LIMIT {MAX_ROWS + 1}").fetchall()
        except psycopg.Error as exc:
            return f"SQL error: {str(exc).strip().splitlines()[0]}"
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        out = json.dumps(rows, default=str)
        return _clip(f"{len(rows)} row(s){' (more not shown)' if truncated else ''}: {out}")

    # --- dispatch -----------------------------------------------------------------
    def call(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            if name == "search_docs":
                return self.search_docs(str(arguments["query"]))
            if name == "rule_history":
                return self.rule_history(str(arguments["dataset"]), str(arguments["rule_id"]))
            if name == "run_sql":
                return self.run_sql(str(arguments["sql"]))
        except KeyError as exc:
            return f"Missing argument {exc} for {name}."
        return f"Unknown tool {name!r}. Available: search_docs, rule_history, run_sql."
