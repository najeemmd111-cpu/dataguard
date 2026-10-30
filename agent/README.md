# Knowledge search and evaluation (Phase 3, part A)

Searches the rules documentation in [`docs/`](../docs) four different ways, and measures which way finds the right section most often. The root-cause agent (part B) will use the best method to look up causes and fixes.

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

## Tests

```bash
pytest                                          # chunking, metrics, fusion, and that every question points at a real section
TEST_DATABASE_URL=postgresql://... pytest       # plus search tests against PostgreSQL + pgvector
```

The database tests use small offline stand-in models (`DG_EMBEDDER=hashing`), so they need no downloads. They check the code, not the search quality. Reports made with the stand-ins say so at the top.

## Adding knowledge

Add or edit a page in `docs/`, run `ingest` again, and add questions for it to `eval/questions.jsonl`. A test fails if a question points at a section that no longer exists, for example after renaming a heading.
