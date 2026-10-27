# DataGuard rules engine

FastAPI service that loads YAML data contracts from `../contracts`, checks PostgreSQL tables against them on a schedule, and stores results in the `dq` schema.

## Rule types

| type | fields | fails when |
|---|---|---|
| `schema` | uses the contract's `schema:` section | a required column is missing or has the wrong type |
| `freshness` | `column`, `max_age` (`30m`, `24h`, `7d`) | `now() - max(column) > max_age` |
| `completeness` | `column`, `min_ratio` (0–1) | share of non-NULL values < `min_ratio` |
| `uniqueness` | `columns: [..]` | any key appears more than once |
| `row_count` | `min` and/or `max` | row count outside the bounds |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | DB connectivity |
| POST | `/runs` `{dataset?}` | run checks now |
| GET | `/runs`, `/runs/{id}` | run history / one run with results |
| GET | `/datasets`, `/datasets/{name}` | health per dataset / contract + latest results |
| GET | `/failures?severity=&dataset=` | currently failing rules |
| POST | `/rules` `{dataset, rule}` | add a rule at runtime (stored in `dq.custom_rules`) |
| POST | `/results/{id}/annotations` `{note, author}` | annotate a result |
| GET | `/audit` | MCP audit log |
| GET | `/llm-calls` | phase 3 cost log |

Interactive docs: http://localhost:8000/docs

## Run locally without Docker for the engine

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -r ../db/requirements.txt
docker compose up -d postgres seed          # from the repo root
uvicorn app.main:app --reload
```

## Tests

```bash
pytest                                       # starts Postgres with Testcontainers (needs Docker)
TEST_DATABASE_URL=postgresql://... pytest    # or use an existing database (it gets reset!)
```
