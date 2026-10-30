# Writing a data contract

## What a contract is

A data contract is a YAML file in the `contracts/` folder that states what a dataset promises: who owns it, which table it lives in, its columns and types, and the rules it must pass. The rules engine loads every contract at start-up and checks them on the contract's schedule.

## Minimal example

```yaml
dataset: payments
table: public.payments
owner: finance-data-team
schedule: "*/30 * * * *"
schema:
  - { name: payment_id, type: integer, required: true }
  - { name: paid_at,    type: timestamp, required: true }
rules:
  - { id: payments_fresh, type: freshness, column: paid_at, max_age: 2h, severity: critical }
```

## Required fields

`dataset` is the name shown in the dashboard. `table` is the PostgreSQL table, optionally with a schema prefix. `owner` is the team that fixes failures. `rules` lists the checks; each rule needs a unique lowercase `id` and a `type`.

## Schedule

`schedule` is a cron expression in UTC. `"*/15 * * * *"` means every 15 minutes, `"0 * * * *"` every hour on the hour, and `"0 */6 * * *"` every six hours. Without a schedule, the contract is checked only when someone runs the checks.

## Validation errors

Contracts are validated when they load. Unknown fields, duplicate rule ids, an invalid `max_age` like `24` without a unit, or a column name with spaces or semicolons are rejected with a clear message, and the engine does not start until the file is fixed.

## Adding rules without editing YAML

Rules can also be added at run time through the API or the MCP `add_rule` tool. They are stored in the `dq.custom_rules` table and merged with the YAML. If a runtime rule has the same id as a YAML rule, the YAML rule wins.
