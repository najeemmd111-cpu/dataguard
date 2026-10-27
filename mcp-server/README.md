# DataGuard MCP server

Exposes the rules engine to AI agents over the Model Context Protocol (stdio transport).

| Tool | Kind | Roles |
|---|---|---|
| `list_failures(severity?, dataset?, limit?)` | read | reader, editor |
| `list_datasets()` | read | reader, editor |
| `get_dataset(name)` | read | reader, editor |
| `get_run(run_id)` | read | reader, editor |
| `run_checks(dataset?)` | write | editor |
| `add_rule(dataset, rule)` | write | editor |
| `annotate_anomaly(result_id, note)` | write | editor |

Every call (allowed, denied, or failed) is written to `dq.audit_log` with the client name, role and arguments. Roles live in `permissions.json`.

## Run

```bash
npm install
npm run build
npm test                 # in-memory MCP client, no database needed
npm run inspect          # opens the MCP Inspector in your browser
```

The rules engine (`http://localhost:8000`) and Postgres must be running (`docker compose up` at the repo root).

## Connect Claude Desktop

Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "dataguard": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/dataguard/mcp-server/dist/index.js"],
      "env": {
        "MCP_ROLE": "editor",
        "ENGINE_URL": "http://localhost:8000",
        "DATABASE_URL": "postgresql://dataguard:dataguard@localhost:5432/dataguard"
      }
    }
  }
}
```

## Connect Claude Code

```bash
claude mcp add dataguard --env MCP_ROLE=reader -- node /ABSOLUTE/PATH/TO/dataguard/mcp-server/dist/index.js
```

Then ask: *"What critical data-quality failures are there, and what do the sample rows show?"*

## Next (optional)

- Add the Streamable HTTP transport (`@modelcontextprotocol/sdk/server/streamableHttp.js`) so remote clients can connect.
- Pass the role per client with an API key header instead of an env var.
