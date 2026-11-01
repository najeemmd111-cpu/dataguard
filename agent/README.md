# Knowledge search and root-cause agent (Phase 3)

**Part A** searches the rules documentation in [`docs/`](../docs) four different ways, and measures which way finds the right section most often. **Part B** is an agent that uses the best method, the data itself and a local language model to explain why a rule failed.

## How it works

1. **Chunking.** Each page is split into sections at its `##` headings, about 110 sections from 22 pages. Long sections are split again into overlapping parts. Every section has a stable id such as `runbook-orders#orders-fresh-fails`.
2. **Indexing.** Each chunk is stored in `dq.doc_chunks` with:
   - an **embedding** from [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (384 numbers that capture meaning), in a **pgvector** column with an HNSW index
   - a **tsvector** for PostgreSQL full-text search, with a GIN index
3. **Search**, four ways:

| Method | How it ranks |
|---|---|
| `keyword` | PostgreSQL full-text search, ranked with `ts_rank_cd` (BM25-like, not BM25) |
| `vector` | Cosine similarity between the question's embedding and each chunk's (pgvector) |
| `hybrid` | Both lists merged with Reciprocal Rank Fusion: each list gives a chunk `1 / (60 + rank)` |
| `hybrid_rerank` | The top 20 hybrid results re-scored by a cross-encoder ([`ms-marco-MiniLM-L-6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2)), which reads the question and the passage together |

The models run with [fastembed](https://github.com/qdrant/fastembed) on ONNX Runtime: no PyTorch, about 90 MB per model, downloaded once and cached.

## Run it (Docker, recommended on a Mac)

The database must be running (`docker compose up -d` in the repo root). Then, from the repo root:

```bash
docker compose run --rm agent ingest                                  # index docs/ (first run downloads the models)
docker compose run --rm agent search "why are orders three days old?"  # try a question
docker compose run --rm agent evaluate                                # compare the four methods
```

`evaluate` prints a results table and saves it to `agent/eval/results.md` and `results.json`.

Try one method at a time: `docker compose run --rm agent search "…" --method keyword`.

## Run it with local Python (3.10 or newer)

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m dataguard_agent ingest
python -m dataguard_agent evaluate
```

## The evaluation

[`eval/questions.jsonl`](eval/questions.jsonl) holds 53 questions. Each one lists the section or sections that answer it.

- **25 `exact` questions** reuse words from the docs, such as rule ids and setting names: *"orders_unique_id fails, what should I do?"*
- **28 `paraphrase` questions** describe the same needs in other words: *"Every row from yesterday's batch shows up twice."*

The split shows where each method is strong. Keyword search finds exact terms; embeddings should do better when the words differ.

Metrics, per method:

- **Hit@1**: the answer section is ranked first.
- **Recall@5**: the answer section is in the top 5. This is what an agent would read.
- **MRR@10**: the mean of 1 / rank of the answer section.
- **Latency**: median and 95th percentile per question, including embedding the question.

CI runs the same evaluation with the real models on every push and shows the table in the run's summary (Actions → the run → `agent` job summary).

## Results

| Method | Hit@1 | Recall@5 | MRR@10 | Recall@5 (exact) | Recall@5 (paraphrase) | Median latency | p95 latency |
|---|---|---|---|---|---|---|---|
| Keyword (PostgreSQL full-text) | 0.58 | **0.87** | 0.69 | 1.00 | 0.75 | 0 ms | 1 ms |
| Vector (pgvector embeddings) | 0.68 | **0.94** | 0.79 | 0.96 | 0.93 | 4 ms | 6 ms |
| Hybrid (RRF of both) | 0.70 | **0.93** | 0.80 | 0.96 | 0.89 | 4 ms | 8 ms |
| Hybrid + cross-encoder re-rank | 0.83 | **0.96** | 0.89 | 1.00 | 0.93 | 235 ms | 288 ms |

Full report, including the questions that were missed: [eval/results.md](eval/results.md).

## Part B: the root-cause agent

Ask why a rule failed:

```bash
ollama pull qwen2.5:3b                                        # once; Ollama must be running
docker compose run --rm agent investigate orders_fresh        # add -v to see every tool call
docker compose run --rm agent evaluate-agent                  # grade it on the 4 failures with a known cause
```

How an investigation works:

1. **Gather** (code, no model): the failing result (measured value, threshold, sample rows) and the 4 most relevant doc sections from the re-ranked search. Even a small model starts well informed.
2. **Investigate** (model + tools, at most 4 rounds): the model can call
   - `search_docs`: the re-ranked hybrid search from part A
   - `rule_history`: when the rule started failing
   - `run_sql`: one read-only `SELECT` to check the data
3. **Answer:** the model writes JSON that must match a schema (`summary`, `likely_cause`, `evidence`, `fix_steps`, `confidence`, `sources`). Ollama enforces the schema, and the answer is validated, with one retry. Cited sources the model was never shown are removed and recorded.

**Safety of `run_sql`.** Queries run as a separate database user (`dataguard_agent_ro`) that can only `SELECT` from the business tables and `dq.results`/`dq.runs`. Its sessions are read-only, time out after 5 seconds, and return at most 20 rows. Only a single `SELECT` is accepted. Tests check that a `DELETE` hidden inside a `WITH` clause is blocked and that `dq.audit_log` cannot be read.

**Logging.** Every model call is written to `dq.llm_calls` (step, model, tokens in and out, cost, latency, success or error). Every investigation is written to `dq.investigations` with its answer and full trace. The dashboard shows the latest explanation under each failure, and an **AI usage** page summarises calls, tokens and response times.

**Model.** By default `qwen2.5:3b` through Ollama, free and on your own machine. Use another Ollama model with `DG_LLM_MODEL=llama3.2:3b docker compose run --rm agent …`. For a paid hosted model, set `DG_PRICE_IN_PER_MTOK` and `DG_PRICE_OUT_PER_MTOK` so costs are computed.

**Grading.** `evaluate-agent` runs the agent on the 4 seeded failures, whose real causes are known, and grades each answer:

- **Right cause**: the summary and likely cause name the real cause (for example a stopped ETL job), not just any part of the answer
- **No false claims**: it does not claim to have changed data (the agent can only read) or state a known wrong conclusion (for example "not the ETL job")
- **Cites a right doc**: at least one cited section explains this failure
- **Correct**: all of the above, with a valid answer
- **Key facts**: the share of expected facts mentioned anywhere

Grading uses keywords, not a second model, so it is simple and transparent, but it does not judge reasoning quality. Results are saved to `eval/agent_results.md`. `regrade <ids>` re-scores saved investigations, for example to compare answers from before and after a prompt change with the same grader.

A first version of the grader only checked sources and keywords anywhere in the answer. It reported 100% "cites a right doc" while 2 of 4 answers were wrong: one blamed the database connection instead of the stopped ETL job, and one claimed to have deleted 10,025 rows, which the read-only agent cannot do. The stricter checks above came from reading those answers.

**False-claim guard.** After each answer, a check looks for claims of actions the agent cannot take ("deleted 10,025 rows", "was fixed", "executed successfully"). If it finds one, the answer gets a warning, its confidence is set to low, and the dashboard shows the warning above the explanation.

## Tests

```bash
pytest                                          # chunking, metrics, fusion, and that every question points at a real section
TEST_DATABASE_URL=postgresql://... pytest       # plus search and agent tests against PostgreSQL + pgvector (42 tests)
```

The database tests use small offline stand-in models (`DG_EMBEDDER=hashing`) and a scripted language model that replays prepared replies, so they need no downloads and no Ollama. They test tool calls, the round limit, retries, the read-only user, and logging. They check the code, not the search quality. Reports made with the stand-ins say so at the top.

## Adding knowledge

Add or edit a page in `docs/`, run `ingest` again, and add questions for it to `eval/questions.jsonl`. A test fails if a question points at a section that no longer exists, for example after renaming a heading.
