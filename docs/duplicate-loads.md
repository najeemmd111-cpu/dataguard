# Duplicate loads

## What happens

The same batch of data is inserted more than once. Every row in the batch then appears twice, so totals double and keys that should be unique are repeated.

## Typical causes

- **A retry after a timeout.** The first attempt actually succeeded, but the job did not receive the confirmation and ran the insert again.
- **Two schedulers run the same job,** for example after a migration where the old scheduler was not switched off.
- **A manual re-run** to fix one problem reloaded a period that was already there.
- **Append-only loads without a key,** so nothing stops a second copy.

## Symptoms

The uniqueness rule fails and most duplicated keys appear exactly twice. The row count jumps by the size of one batch. The duplicated rows have identical values and close `created_at` timestamps.

## How to clean up

Keep one row per key, usually the most recent, and delete the rest inside a transaction. Check the row count and the uniqueness rule afterwards. Then fix the cause, not only the data.

## Preventing it

Make loads idempotent: write with an upsert on the business key (`INSERT ... ON CONFLICT (order_id) DO UPDATE`), and add a `UNIQUE` constraint once the table is clean. An idempotent load can be re-run safely any number of times.
