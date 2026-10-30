# Partial loads

## What happens

A load finishes without errors but brings in only part of the data. For example the source export timed out after the first file, or a pagination loop stopped early.

## Symptoms

Freshness may pass, because some new rows did arrive, while the row count is lower than usual for the period. Totals in reports drop suddenly. Some categories, regions or days are missing entirely.

## How to confirm it

Count rows per day for the last two weeks and compare with the same weekday before. A day with a fraction of the usual volume is a strong sign. Compare with the source system's own count for that day if you can.

## What to do

Reload the affected period completely. Because a partial reload can create duplicates, use an idempotent upsert or delete the period first inside the same transaction.

## Preventing it

Have the load job compare the number of rows it read from the source with the number it wrote, and fail loudly if they differ. A row count rule with a sensible `min` catches the largest gaps.
