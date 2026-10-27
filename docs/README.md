# Rules documentation (RAG corpus)

The root-cause agent searches these pages in phase 3. Aim for 20–30 short pages, one topic each, with clear `##` headings (chunks are split by heading).

Suggested pages:

- One per rule type: `freshness.md`, `completeness.md`, `uniqueness.md`, `schema.md`, `row-count.md`
- `severity-levels.md` — what critical/high/medium/low mean and who gets alerted
- `thresholds.md` — how to choose `max_age`, `min_ratio`
- Root causes: `late-etl-jobs.md`, `upstream-schema-change.md`, `duplicate-loads.md`, `partial-loads.md`, `timezone-bugs.md`
- Runbooks: `runbook-orders.md`, `runbook-customers.md`
- `contracts-howto.md` — writing a YAML contract

Two starter pages are included: `freshness.md` and `uniqueness.md`.
