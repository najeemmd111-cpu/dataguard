# Timezone problems

## What happens

A timestamp is written in one timezone and read as another. A local Paris time stored in a `timestamp without time zone` column is later read as UTC, so every value is one or two hours off.

## Symptoms

The freshness rule reports an age that is consistently off by a whole number of hours, sometimes even a negative age, meaning the newest row appears to be in the future. Daily totals shift between days around midnight.

## Daylight saving time

Problems often appear twice a year, when clocks change. A job that runs at "02:30 local time" may run twice or not at all on those nights, and hourly reports show a missing or doubled hour.

## How to confirm it

Compare a few timestamps with the source system for the same records. If the difference is exactly one or two hours, it is a timezone problem, not a late load.

## Fix

Store timestamps as `timestamp with time zone` and convert to UTC at load time. Run schedules in UTC; DataGuard's contract schedules are always UTC.
