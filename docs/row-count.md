# Row count rule

## What it checks

A row count rule counts all rows in the table and fails when the count is below `min` or above `max`. You can set one bound or both. It is the simplest guard against an empty table, a truncated load, or a runaway duplicate load.

## Configuration

```yaml
- id: orders_min_rows
  type: row_count
  min: 1000
  severity: medium
```

## Choosing the bounds

Set `min` well below the normal size, so normal growth and seasonal dips do not trigger it. A good start is half the smallest count seen in the last month. Set `max` only when a sudden jump would be a problem, for example a table that should stay around 50 products.

## Common causes of a failure

- **Below `min`:** the load truncated the table and then failed before inserting, a filter in the ETL removed most rows, or the job pointed at the wrong source.
- **Above `max`:** the same batch was loaded several times, or a join multiplied rows.

## Fix

For a count that is too low, check the load job's logs and restore the last good load. For a count that is too high, run the uniqueness checks too: a jump in rows usually comes with duplicate keys. See duplicate loads.
