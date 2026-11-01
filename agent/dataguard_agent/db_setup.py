"""Tables and the read-only database user the agent needs. Safe to run any number of times."""

from __future__ import annotations

import psycopg
from psycopg import sql

from .config import Settings

TABLES_SQL = """
CREATE SCHEMA IF NOT EXISTS dq;

CREATE TABLE IF NOT EXISTS dq.llm_calls (
    call_id        BIGSERIAL PRIMARY KEY,
    at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    purpose        TEXT NOT NULL,
    model          TEXT NOT NULL,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd       NUMERIC(12, 6) NOT NULL DEFAULT 0,
    latency_ms     INTEGER NOT NULL DEFAULT 0,
    success        BOOLEAN NOT NULL DEFAULT true,
    error          TEXT
);
ALTER TABLE dq.llm_calls ADD COLUMN IF NOT EXISTS investigation_id BIGINT;

CREATE TABLE IF NOT EXISTS dq.investigations (
    investigation_id BIGSERIAL PRIMARY KEY,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    dataset          TEXT NOT NULL,
    rule_id          TEXT NOT NULL,
    result_id        BIGINT,
    model            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'running',   -- running | ok | error
    answer           JSONB,
    trace            JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_calls       INTEGER NOT NULL DEFAULT 0,
    input_tokens     INTEGER NOT NULL DEFAULT 0,
    output_tokens    INTEGER NOT NULL DEFAULT 0,
    latency_ms       INTEGER NOT NULL DEFAULT 0,
    error            TEXT
);
CREATE INDEX IF NOT EXISTS investigations_rule_idx ON dq.investigations (dataset, rule_id, created_at DESC);
"""

# What the agent's own SQL may read. Nothing else, and never write.
READABLE_TABLES = ["public.orders", "public.customers", "public.products", "dq.results", "dq.runs"]


def setup(conn: psycopg.Connection, settings: Settings) -> None:
    with conn.transaction():
        conn.execute(TABLES_SQL)

        user = sql.Identifier(settings.readonly_user)
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (settings.readonly_user,)).fetchone()
        if exists:
            conn.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(user, sql.Literal(settings.readonly_password)))
        else:
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(user, sql.Literal(settings.readonly_password)))
        # Even if a grant were too wide, every session of this user is read-only and time-limited.
        conn.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(user))
        conn.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '5s'").format(user))

        db = conn.execute("SELECT current_database() AS d").fetchone()
        dbname = db["d"] if isinstance(db, dict) else db[0]
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(dbname), user))
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public, dq TO {}").format(user))
        for table in READABLE_TABLES:
            schema, name = table.split(".")
            if conn.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (table,)).fetchone():
                conn.execute(
                    sql.SQL("GRANT SELECT ON {}.{} TO {}").format(sql.Identifier(schema), sql.Identifier(name), user)
                )
