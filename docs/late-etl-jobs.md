# Late or stopped ETL jobs

## Symptoms

The freshness rule fails, the newest `updated_at` stays at the same value across several checks, and the row count stops growing. Usually every table loaded by the same job goes stale at the same time.

## Common reasons a job stops

- **The scheduler is paused or the job was disabled** during maintenance and never re-enabled.
- **Credentials expired.** The job fails at the first connection to the source, often after a password rotation.
- **The job is stuck,** for example waiting on a lock held by another process, so it never finishes and the next run is skipped.
- **The server ran out of disk space,** so writes fail.

## How to confirm it

Compare the age measured by the freshness rule with the job's last successful run in the scheduler. If the job's last success matches the newest timestamp in the table, the job is the cause. Check the other tables the same job loads: if they are stale too, you have confirmed it.

## What to do

Restart or repair the job, then trigger a catch-up run so the missing period is loaded. Run the dataset's checks afterwards to confirm freshness is back. Add a note to the failure explaining what happened, so the next person sees the history.

## Preventing it

Alert on job failures in the scheduler itself, not only on data freshness. Freshness alerts catch the problem later, after downstream users may already have seen old data.
