# Alerts with n8n (Phase 4)

When a rule **starts failing** or **recovers**, the rules engine sends an event to an n8n workflow, which emails the team and, for new critical failures, posts to Slack.

```
rules engine ──POST events──▶ n8n webhook ──▶ Format alert ──▶ Send email (Mailpit)
                                                     └──▶ new critical failure and Slack set up? ──▶ Post to Slack
```

## Start it

```bash
docker compose --profile alerts up -d
```

This starts **n8n** (http://localhost:5678) and **Mailpit**, a fake inbox (http://localhost:8025). On every start, n8n imports `workflows/dataguard-alerts.json` and publishes it, so there is nothing to click. The first time you open n8n, it asks you to create a local owner account; the webhook works without it.

Give n8n about 30 seconds after starting before sending alerts; until then the webhook answers 404.

## Try it

```bash
curl -X POST localhost:8000/alerts/test          # sends the currently failing rules as a test alert
```

Open http://localhost:8025 to read the email.

To see real alerts, simulate the sales ETL catching up and then stopping again:

```bash
# 1. The ETL "catches up": one fresh row makes orders_fresh pass → a "recovered" email
docker compose exec postgres psql -U dataguard -c "UPDATE orders SET updated_at = now() WHERE id = 1"
curl -X POST localhost:8000/runs -H 'content-type: application/json' -d '{"dataset":"orders"}'

# 2. The ETL "stops" again → a "failing (critical)" email, and a Slack message if Slack is set up
docker compose exec postgres psql -U dataguard -c "UPDATE orders SET updated_at = now() - interval '5 days' WHERE id = 1"
curl -X POST localhost:8000/runs -H 'content-type: application/json' -d '{"dataset":"orders"}'
```

Running the checks again without changing anything sends nothing: that is the point.

## Why only changes are sent

`orders` is checked every 15 minutes and has been failing for days. Alerting after every run would send about 100 identical emails a day, and people would stop reading them. So the engine compares each result with the rule's previous one and sends:

| Event | When |
|---|---|
| `failing` | the rule fails now and passed before (or never ran) |
| `recovered` | the rule passes now and failed before |
| `test` | sent by `POST /alerts/test` |

Each payload also says how many rules are **still failing** from earlier runs, so the email gives the full picture without repeating old alerts. Sending is best effort: if n8n is down, the check run still completes and the engine logs a warning.

## Payload

```json
{
  "source": "dataguard",
  "run_id": 15,
  "sent_at": "2026-11-01T18:40:02+00:00",
  "dashboard_url": "http://localhost:5173",
  "summary": {"failing": 1, "recovered": 0, "test": 0, "still_failing": 2},
  "events": [{
    "type": "failing", "dataset": "orders", "rule_id": "orders_fresh", "rule_type": "freshness",
    "severity": "critical", "owner": "sales-data-team",
    "message": "latest updated_at is ... (72.1h old)", "measured_value": "72.1h", "threshold": "24h",
    "result_id": 1234, "dataset_url": "http://localhost:5173/datasets/orders"
  }]
}
```

## Settings

Set these in a `.env` file next to `docker-compose.yml`:

| Variable | Default | Purpose |
|---|---|---|
| `ALERT_EMAIL_TO` | `data-team@example.com` | who receives alert emails |
| `SLACK_WEBHOOK_URL` | empty (Slack off) | a Slack incoming webhook; new critical failures are posted there |
| `DASHBOARD_URL` | `http://localhost:5173` | used for links in alerts |
| `FAILURE_WEBHOOK_URL` | the n8n webhook | where the engine sends events |

To use Slack, create a free workspace, add an **Incoming Webhook** app to a channel, put its URL in `.env` as `SLACK_WEBHOOK_URL=…`, and restart: `docker compose --profile alerts up -d`.

## Changing the workflow

The message formatting lives in [`format-alert.js`](format-alert.js), so it can be read and reviewed as code. After editing it, rebuild the workflow file and restart n8n:

```bash
python3 n8n/build-workflow.py
docker compose --profile alerts restart n8n
```

Changes made in the n8n editor are overwritten on the next start. Export the workflow first if you want to keep them.

Emails go through Mailpit's HTTP API, so no email credentials are needed. For a real mail server, replace the "Send email" node with n8n's **Send Email** node and an SMTP credential.

## Tested

The workflow was run in n8n 2.45.7 against the real rules engine: a test alert, a recovery and a new critical failure each produced the expected email, only the new critical failure was posted to Slack, and a run with no changes sent nothing. The engine side is covered by `rules-engine/tests/test_alerts.py`.
