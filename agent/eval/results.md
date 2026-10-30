# Retrieval evaluation

53 questions over 112 chunks from 22 pages. Embeddings: `sentence-transformers/all-MiniLM-L6-v2`. Re-ranker: `Xenova/ms-marco-MiniLM-L-6-v2`. Run 2026-10-30 on Linux aarch64.

| Method | Hit@1 | Recall@5 | MRR@10 | Recall@5 (exact) | Recall@5 (paraphrase) | Median latency | p95 latency |
|---|---|---|---|---|---|---|---|
| Keyword (PostgreSQL full-text) | 0.58 | **0.87** | 0.69 | 1.00 | 0.75 | 0 ms | 1 ms |
| Vector (pgvector embeddings) | 0.68 | **0.94** | 0.79 | 0.96 | 0.93 | 4 ms | 6 ms |
| Hybrid (RRF of both) | 0.70 | **0.93** | 0.80 | 0.96 | 0.89 | 4 ms | 8 ms |
| Hybrid + cross-encoder re-rank | 0.83 | **0.96** | 0.89 | 1.00 | 0.93 | 235 ms | 288 ms |

- **Hit@1**: share of questions whose answer section is ranked first.
- **Recall@5**: share of questions whose answer section is in the top 5.
- **MRR@10**: mean of 1 / rank of the answer section (0 if not in the top 10).
- **exact** questions reuse words from the docs (rule ids, settings); **paraphrase** questions describe the problem in other words.

## Questions Hybrid + cross-encoder re-rank missed (not in the top 5)

- `p03` A retry after a network timeout inserted the same data again. How do we stop that happening in future? — expected `duplicate-loads#preventing-it`, top 3: `duplicate-loads#typical-causes, uniqueness#common-causes-of-a-failure, backfills#running-it-safely`
- `p21` Where should I start when something looks wrong with the data? — expected `investigation-checklist#step-1-read-the-result`, top 3: `investigation-checklist#step-5-fix-verify-record, severity-levels#the-four-levels, missing-values#lookups-that-do-not-match`
