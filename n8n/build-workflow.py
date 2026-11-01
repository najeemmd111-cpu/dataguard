"""Build workflows/dataguard-alerts.json from format-alert.js.

Edit the JavaScript in format-alert.js, then run: python3 n8n/build-workflow.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

nodes = [
    {
        "id": "0b5c7e0a-1d2b-4c3d-8e4f-5a6b7c8d9e01",
        "name": "Alert from DataGuard",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [0, 0],
        "webhookId": "5f0d9a6e-2c4b-4e8f-9a1b-3c5d7e9f1a2b",
        "parameters": {"httpMethod": "POST", "path": "dataguard-failure", "responseMode": "onReceived",
                       "options": {}},
    },
    {
        "id": "0b5c7e0a-1d2b-4c3d-8e4f-5a6b7c8d9e02",
        "name": "Format alert",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [240, 0],
        "parameters": {"jsCode": (HERE / "format-alert.js").read_text(encoding="utf-8")},
    },
    {
        "id": "0b5c7e0a-1d2b-4c3d-8e4f-5a6b7c8d9e03",
        "name": "Send email (Mailpit)",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [500, -100],
        "parameters": {
            "method": "POST",
            "url": "={{ $json.mailpitUrl }}/api/v1/send",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ From: { Email: 'dataguard@example.com', Name: 'DataGuard' }, "
                        "To: [{ Email: $json.to }], Subject: $json.subject, Text: $json.text, HTML: $json.html, "
                        "Tags: ['dataguard'] }) }}",
            "options": {},
        },
    },
    {
        "id": "0b5c7e0a-1d2b-4c3d-8e4f-5a6b7c8d9e04",
        "name": "New critical failure and Slack set up?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [500, 120],
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{
                    "id": "8c1f2a3b-4d5e-4f60-8172-93a4b5c6d7e8",
                    "leftValue": "={{ $json.sendSlack }}",
                    "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                }],
                "combinator": "and",
            },
            "options": {},
        },
    },
    {
        "id": "0b5c7e0a-1d2b-4c3d-8e4f-5a6b7c8d9e05",
        "name": "Post to Slack",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [760, 100],
        "parameters": {
            "method": "POST",
            "url": "={{ $json.slackUrl }}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ text: $json.slackText }) }}",
            "options": {},
        },
    },
]

connections = {
    "Alert from DataGuard": {"main": [[{"node": "Format alert", "type": "main", "index": 0}]]},
    "Format alert": {"main": [[
        {"node": "Send email (Mailpit)", "type": "main", "index": 0},
        {"node": "New critical failure and Slack set up?", "type": "main", "index": 0},
    ]]},
    "New critical failure and Slack set up?": {"main": [
        [{"node": "Post to Slack", "type": "main", "index": 0}],
        [],
    ]},
}

workflow = {
    "id": "DgAlerts00000001",
    "name": "DataGuard failure alerts",
    "active": True,
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1"},
    "pinData": {},
    "versionId": "3d6f1e2a-7b8c-4d9e-a0f1-b2c3d4e5f607",
}

out = HERE / "workflows" / "dataguard-alerts.json"
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {out}")
