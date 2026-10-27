# Freshness rule

## What it checks

A freshness rule measures the age of the newest value in a timestamp column, usually `updated_at`: `now() - max(updated_at)`. The rule fails when that age is larger than `max_age`.

## Configuration

```yaml
- id: orders_fresh
  type: freshness
  column: updated_at
  max_age: 24h        # 30m, 24h, 7d
  severity: critical
```

Pick `max_age` as the normal load interval plus a safety margin. A table loaded every 15 minutes might use `2h`; a nightly table `26h`.

## Common causes of a failure

- **The ETL job stopped or is stuck.** Check the scheduler (Airflow, cron, n8n) for failed or still-running jobs.
- **The job runs but loads nothing.** The source returned zero rows, often because of an expired credential or an empty upstream extract.
- **The timestamp is not updated on change.** Rows are inserted but `updated_at` keeps its insert value. Check the trigger or the ETL mapping.
- **Timezone confusion.** A `timestamp without time zone` written in local time can look hours old (or in the future).

## How to investigate

1. Look at `measured_value`: is the age just over the limit (slow job) or days old (stopped job)?
2. Compare `max(created_at)` and `max(updated_at)`: if both are old, nothing is arriving.
3. Check other tables loaded by the same job; if they are also stale, the job is the cause.

## Fix

Restart or repair the load job, then run `run_checks` for the dataset to confirm.
