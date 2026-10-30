# Glossary

## Contract and rule

A **contract** is a YAML file that describes one dataset: its table, owner, schema and rules. A **rule** is one check inside a contract, such as freshness on `updated_at`.

## Run and result

A **run** is one execution of the rules engine over one or all datasets, started by the schedule, the API, the dashboard or an AI tool. A **result** is the outcome of one rule in one run: passed or failed, the measured value, the threshold and sample rows.

## Health

A dataset's **health** summarises its latest results: Failing (red) when a critical or high rule fails, Warning (amber) when only medium or low rules fail, Healthy (green) when all pass.

## Annotation

An **annotation** or note is a comment attached to a result, written by a person or an AI assistant, usually about the cause of a failure.

## Idempotent load

A load is **idempotent** when running it twice gives the same result as running it once, usually because it upserts on a business key instead of appending.
