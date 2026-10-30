# Completeness rule

## What it checks

A completeness rule measures the share of rows where a column is not NULL: `count(column) / count(*)`. The rule fails when that ratio is below `min_ratio`. The sample rows are rows where the column is NULL, so you can see which records are affected.

## Configuration

```yaml
- id: customers_email_complete
  type: completeness
  column: email
  min_ratio: 0.99
  severity: high
```

`min_ratio` is a number between 0 and 1. `0.99` means at most 1% of rows may have no value. Use `1.0` only for columns that must never be empty, such as primary keys or foreign keys that drive billing.

## Common causes of a failure

- **The source system allows empty values.** A web form made the field optional, or an API stopped sending it.
- **A join in the load lost matches.** A LEFT JOIN to a lookup table returns NULL when the lookup is missing or late.
- **A new column was added without a backfill.** Old rows have NULL because nobody filled the history.
- **Mapping error in the ETL.** The source field was renamed, so the target column receives NULL for every new row.

## How to investigate

1. Look at the sample rows: are they recent (a new problem) or spread over years (an old gap)?
2. Group the NULL rows by `created_at` date. A sudden jump on one day points to a deployment or source change on that day.
3. Group by another column such as `country` or `channel`. If all NULLs share one value, the problem is in that one source.

## Fix

Fix the source or the mapping first, then backfill the missing values if they can be recovered. If a share of empty values is normal for the business, lower `min_ratio` deliberately and write down why in the rule's `description`.
