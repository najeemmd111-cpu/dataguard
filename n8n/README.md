# Alerting workflow (Phase 4) — n8n

## Add to docker-compose.yml

```yaml
  n8n:
    image: n8nio/n8n
    ports: ["5678:5678"]
    volumes: ["n8n_data:/home/node/.n8n"]

  mailpit:                 # fake inbox: http://localhost:8025
    image: axllent/mailpit
    ports: ["8025:8025", "1025:1025"]
```

(and `n8n_data:` under `volumes:`)

Then give the rules engine `FAILURE_WEBHOOK_URL: http://n8n:5678/webhook/dataguard-failure`. The engine already POSTs `{run_id, failures: [...]}` after every run that has failures (see `rules-engine/app/runner.py`).

## Workflow

1. **Webhook** node — POST, path `dataguard-failure`
2. **Split Out** on `body.failures`
3. **IF** `severity` is `critical`
   - true → **Slack** node (incoming webhook of a free test workspace)
   - false → **Send Email** node (SMTP host `mailpit`, port `1025`, no auth)

Export it (⋯ → Download) as `n8n/dataguard-failure-alerts.json` and commit it.
