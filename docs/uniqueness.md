# Uniqueness rule

## What it checks

A uniqueness rule groups rows by the listed key columns and fails if any key appears more than once. The sample rows show the duplicated keys and how many times each appears.

## Configuration

```yaml
- id: orders_unique_id
  type: uniqueness
  columns: [order_id]
  severity: critical
```

Use several columns for a composite key, e.g. `columns: [order_id, line_number]`.

## Common causes of a failure

- **A load ran twice.** A retry after a timeout inserted the same batch again. Duplicates then share the same `created_at` range.
- **Append instead of upsert.** The job inserts changed rows instead of updating them, so every change adds a copy.
- **Missing constraint.** The table has no `UNIQUE` constraint, so the database cannot block duplicates.
- **Source system duplicates.** The upstream extract itself contains repeats.

## How to investigate

1. Check `occurrences` in the sample rows: exactly 2 everywhere suggests one double load.
2. Compare the duplicated rows: identical rows point to a re-run; different values point to append-instead-of-upsert.

## Fix

Delete the extra copies (keep the latest per key), make the load idempotent (upsert on the key), and add a `UNIQUE` constraint once the data is clean.
