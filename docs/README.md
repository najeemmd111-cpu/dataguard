# Rules documentation

The knowledge base that the search, and later the root-cause agent, use to explain failures. There are 20 pages, one topic each. Every `##` heading starts a section that can be found on its own, so keep sections short and give each one a heading that says what it answers.

| Kind | Pages |
|---|---|
| Rule types | `freshness`, `completeness`, `uniqueness`, `schema`, `row-count` |
| Settings | `severity-levels`, `thresholds`, `contracts-howto` |
| Root causes | `late-etl-jobs`, `upstream-schema-change`, `duplicate-loads`, `partial-loads`, `timezone-bugs`, `missing-values` |
| Procedures | `investigation-checklist`, `backfills`, `alerting-and-ownership`, `mcp-tools` |
| Runbooks | `runbook-orders`, `runbook-customers`, `runbook-products` |
| Reference | `glossary` |

This README is not indexed. After editing pages, re-index with `docker compose run --rm agent ingest`. See `agent/README.md`.
