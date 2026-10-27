# Agent, hybrid RAG and evaluation (Phase 3)

Planned layout:

```
agent/
  requirements.txt        # sentence-transformers, rank_bm25, psycopg, an LLM SDK
  llm.py                  # ONE helper for every LLM call -> writes dq.llm_calls
  prices.yaml             # $/1M tokens per model, used to compute cost_usd
  ingest.py               # chunk docs/*.md by heading, embed, store in doc_chunks
  retrieve.py             # keyword, vector, hybrid (RRF), hybrid + cross-encoder re-rank
  root_cause.py           # agent loop: MCP tools + read-only SQL + doc search -> {cause, evidence, fix}
  eval/
    questions.jsonl       # 40–60 {question, relevant_chunk_ids, reference_answer}
    eval_retrieval.py     # recall@5 and MRR for the 4 retrieval setups
    eval_answers.py       # LLM-as-judge: correctness + faithfulness
```

## Table to add (put it in db/init.sql when you start)

```sql
CREATE TABLE dq.doc_chunks (
  chunk_id   TEXT PRIMARY KEY,          -- e.g. 'freshness.md#common-causes'
  source     TEXT NOT NULL,
  heading    TEXT,
  content    TEXT NOT NULL,
  embedding  vector(384),               -- all-MiniLM-L6-v2
  tsv        tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);
CREATE INDEX ON dq.doc_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON dq.doc_chunks USING gin (tsv);
```

## Honesty note for the README / CV

Postgres `ts_rank_cd` is BM25-*like*, not BM25. Either call it "full-text search", or use `rank_bm25` / ParadeDB `pg_search` for real BM25.

## Safety

- The agent's SQL runs as a read-only role: `CREATE ROLE dq_agent LOGIN PASSWORD '...'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO dq_agent;`
- Cap the loop (e.g. 8 steps) and the tokens per run.
