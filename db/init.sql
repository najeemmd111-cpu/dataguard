-- DataGuard database bootstrap.
-- Runs once, the first time the Postgres container starts with an empty volume.

-- pgvector is used in phase 3 (hybrid RAG). The pgvector/pgvector image ships it;
-- on a plain Postgres this only prints a notice, so phases 1-2 still work.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pgvector not available: %', SQLERRM;
END $$;

-- ---------------------------------------------------------------
-- Sample business data (the dataset being checked)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id  INTEGER PRIMARY KEY,
    email        TEXT,                      -- some NULLs injected on purpose
    country      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    category     TEXT,
    price        NUMERIC(10, 2) NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- order_id deliberately has NO unique constraint, so duplicates can exist,
-- and amount is deliberately TEXT so the schema check finds a type mismatch.
CREATE TABLE IF NOT EXISTS orders (
    id           BIGSERIAL PRIMARY KEY,
    order_id     INTEGER NOT NULL,
    customer_id  INTEGER,
    product_id   INTEGER,
    quantity     INTEGER NOT NULL,
    amount       TEXT,
    status       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL
);

-- ---------------------------------------------------------------
-- DataGuard's own tables
-- ---------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS dq;

CREATE TABLE IF NOT EXISTS dq.runs (
    run_id       BIGSERIAL PRIMARY KEY,
    trigger      TEXT NOT NULL,             -- 'manual' | 'schedule' | 'api'
    dataset      TEXT,                      -- NULL = all datasets
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    status       TEXT NOT NULL DEFAULT 'running',  -- running | passed | failed | error
    total_rules  INTEGER NOT NULL DEFAULT 0,
    failed_rules INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dq.results (
    result_id      BIGSERIAL PRIMARY KEY,
    run_id         BIGINT NOT NULL REFERENCES dq.runs(run_id) ON DELETE CASCADE,
    dataset        TEXT NOT NULL,
    rule_id        TEXT NOT NULL,
    rule_type      TEXT NOT NULL,
    severity       TEXT NOT NULL,
    passed         BOOLEAN NOT NULL,
    measured_value TEXT,
    threshold      TEXT,
    message        TEXT,
    sample_rows    JSONB NOT NULL DEFAULT '[]'::jsonb,
    checked_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS results_dataset_idx ON dq.results (dataset, checked_at DESC);
CREATE INDEX IF NOT EXISTS results_failed_idx  ON dq.results (passed, severity);

-- Rules added at runtime (API / MCP add_rule). Merged with the YAML contracts.
CREATE TABLE IF NOT EXISTS dq.custom_rules (
    id          BIGSERIAL PRIMARY KEY,
    dataset     TEXT NOT NULL,
    rule        JSONB NOT NULL,
    created_by  TEXT NOT NULL DEFAULT 'api',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS custom_rules_uniq ON dq.custom_rules (dataset, (rule->>'id'));

CREATE TABLE IF NOT EXISTS dq.annotations (
    annotation_id BIGSERIAL PRIMARY KEY,
    result_id     BIGINT NOT NULL REFERENCES dq.results(result_id) ON DELETE CASCADE,
    note          TEXT NOT NULL,
    author        TEXT NOT NULL DEFAULT 'api',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every MCP tool call, allowed or denied.
CREATE TABLE IF NOT EXISTS dq.audit_log (
    audit_id    BIGSERIAL PRIMARY KEY,
    at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    client      TEXT NOT NULL,
    role        TEXT NOT NULL,
    tool        TEXT NOT NULL,
    arguments   JSONB NOT NULL DEFAULT '{}'::jsonb,
    allowed     BOOLEAN NOT NULL,
    outcome     TEXT NOT NULL,               -- 'ok' | 'denied' | 'error'
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS audit_at_idx ON dq.audit_log (at DESC);

-- Phase 3: every LLM call (tokens, cost, latency). Created now so the schema is stable.
CREATE TABLE IF NOT EXISTS dq.llm_calls (
    call_id        BIGSERIAL PRIMARY KEY,
    at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    purpose        TEXT NOT NULL,            -- 'agent' | 'judge' | 'rag' | 'explainer'
    model          TEXT NOT NULL,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd       NUMERIC(12, 6) NOT NULL DEFAULT 0,
    latency_ms     INTEGER NOT NULL DEFAULT 0,
    success        BOOLEAN NOT NULL DEFAULT true,
    error          TEXT
);
