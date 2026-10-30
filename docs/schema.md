# Schema rule

## What it checks

A schema rule compares the table's real columns, read from `information_schema.columns`, with the `schema:` section of the contract. It fails when a required column is missing or when a column has a different type than the contract says. Each mismatch is listed in the sample rows with the expected and actual type.

## Type mapping

The contract uses simple type names. Each one accepts several PostgreSQL types:

| Contract type | Accepted PostgreSQL types |
|---|---|
| `integer` | integer, bigint, smallint |
| `numeric` | numeric, double precision, real, integer types |
| `text` | text, character varying, character |
| `timestamp` | timestamp with or without time zone |
| `boolean` | boolean |
| `date` | date |

## Common causes of a failure

- **An upstream team changed a column type.** For example `amount` became `text` because one source sent values like `"12,50"` with a comma.
- **A column was renamed or dropped** in a migration without updating consumers.
- **The table was recreated by a tool** that inferred types from a CSV file, so numbers became text.

## Why a wrong type matters

A numeric column stored as text sorts wrongly ("100" before "20"), cannot be summed without casting, and accepts invalid values like `"N/A"`. Reports that cast it may fail at run time or silently drop rows.

## Fix

Agree on the type with the producer team, then migrate the column: add a new column with the correct type, copy values with an explicit cast, check for values that fail the cast, and swap the columns. Update the contract only if the new type is the intended one.
