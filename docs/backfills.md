# Backfills and reloads

## When you need one

A backfill reloads or recomputes a past period: after a stopped job, a partial load, a mapping fix, or a new column that needs history.

## Before you start

Tell the dataset's users that numbers for the period will change. Note the current row count and totals for the period, so you can compare afterwards. Pause the scheduled load if it could run at the same time as the backfill.

## Running it safely

Reload one period at a time, for example one day, inside a transaction: delete the period, insert it again, then commit. Or use an upsert on the business key so the load can be repeated safely. Never append a period that is already partly there.

## After the backfill

Run the dataset's checks. Freshness, completeness and uniqueness should pass. Compare totals with the source system and with your notes from before.

## Annotating the failure

Add a note to the failure that triggered the backfill, saying what period was reloaded and why. Notes stay with the result, so the next investigation starts with that history.
