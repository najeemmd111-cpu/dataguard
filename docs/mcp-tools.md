# Using DataGuard from an AI assistant

## What the MCP server offers

DataGuard includes an MCP server, so AI assistants such as Claude Desktop can query data quality directly. Read tools: `list_failures`, `list_datasets`, `get_dataset` and `get_run`. Write tools: `run_checks`, `add_rule` and `annotate_anomaly`.

## Roles and permissions

Each connection runs with a role. A `reader` can only use read tools. An `editor` can also run checks, add rules and annotate results. A reader that calls a write tool gets a "Permission denied" answer. Roles are defined in `mcp-server/permissions.json`.

## The audit log

Every tool call is recorded in `dq.audit_log`: the time, the client, the role, the tool, its arguments, and whether it was allowed. Refused calls and calls that failed are recorded too. The dashboard shows this log on the AI access log page.

## Setting the role in the MCP Inspector

The MCP Inspector does not pass your shell's environment to the server, so `MCP_ROLE=editor npm run inspect` has no effect. Use `npm run inspect:editor`, which passes the role with the Inspector's `-e` option.

## Good questions to ask

"Which critical failures are there?", "Show me the sample rows for orders_unique_id", or "Add a note to result 13 saying the sales ETL is paused." The assistant uses the tools to answer from live data instead of guessing.
