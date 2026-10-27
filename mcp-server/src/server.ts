import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

import type { EngineClient } from "./api.js";
import type { AuditLogger } from "./audit.js";
import { isAllowed, type PermissionConfig } from "./permissions.js";

export interface ServerDeps {
  engine: EngineClient;
  audit: AuditLogger;
  permissions: PermissionConfig;
  role: string;
  /** Fallback client name when the MCP client does not send one. */
  clientName: string;
}

const severity = z.enum(["low", "medium", "high", "critical"]);

const ruleSchema = z
  .object({
    id: z.string().regex(/^[a-z0-9_\-]+$/, "lowercase letters, digits, _ or -"),
    type: z.enum(["schema", "freshness", "completeness", "uniqueness", "row_count"]),
    severity: severity.optional(),
    description: z.string().optional(),
    column: z.string().optional().describe("freshness / completeness"),
    max_age: z.string().optional().describe("freshness, e.g. 24h"),
    min_ratio: z.number().min(0).max(1).optional().describe("completeness"),
    columns: z.array(z.string()).optional().describe("uniqueness"),
    min: z.number().int().optional().describe("row_count"),
    max: z.number().int().optional().describe("row_count"),
  })
  .describe("A data-quality rule. The rules engine validates it fully.");

function asText(data: unknown): CallToolResult {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
}

export function createServer(deps: ServerDeps): McpServer {
  const server = new McpServer({ name: "dataguard", version: "0.1.0" });

  const clientName = () => server.server.getClientVersion()?.name ?? deps.clientName;

  /** Every tool goes through this: permission check, call, audit row. */
  function guarded<A>(tool: string, handler: (args: A) => Promise<unknown>) {
    return async (args: A): Promise<CallToolResult> => {
      const base = { client: clientName(), role: deps.role, tool, args };
      if (!isAllowed(deps.permissions, deps.role, tool)) {
        await deps.audit.write({ ...base, allowed: false, outcome: "denied", detail: "role lacks permission" });
        return {
          isError: true,
          content: [{ type: "text", text: `Permission denied: role "${deps.role}" cannot call "${tool}".` }],
        };
      }
      try {
        const result = await handler(args);
        await deps.audit.write({ ...base, allowed: true, outcome: "ok" });
        return asText(result);
      } catch (err) {
        const message = (err as Error).message;
        await deps.audit.write({ ...base, allowed: true, outcome: "error", detail: message });
        return { isError: true, content: [{ type: "text", text: message }] };
      }
    };
  }

  // ---------------- read tools ----------------
  server.registerTool(
    "list_failures",
    {
      title: "List failing data-quality rules",
      description: "Rules whose latest check failed, most severe first. Includes measured value, threshold and sample rows.",
      inputSchema: {
        severity: severity.optional(),
        dataset: z.string().optional(),
        limit: z.number().int().min(1).max(200).optional(),
      },
      annotations: { readOnlyHint: true },
    },
    guarded("list_failures", (a: { severity?: string; dataset?: string; limit?: number }) =>
      deps.engine.listFailures(a),
    ),
  );

  server.registerTool(
    "list_datasets",
    {
      title: "List datasets",
      description: "Every dataset under contract with its owner, schedule and health (green / amber / red).",
      inputSchema: {},
      annotations: { readOnlyHint: true },
    },
    guarded("list_datasets", () => deps.engine.listDatasets()),
  );

  server.registerTool(
    "get_dataset",
    {
      title: "Show a dataset",
      description: "A dataset's contract (schema and rules) plus the latest result of each rule and any annotations.",
      inputSchema: { name: z.string() },
      annotations: { readOnlyHint: true },
    },
    guarded("get_dataset", (a: { name: string }) => deps.engine.getDataset(a.name)),
  );

  server.registerTool(
    "get_run",
    {
      title: "Show a check run",
      description: "One run of the rules engine with all its results.",
      inputSchema: { run_id: z.number().int().positive() },
      annotations: { readOnlyHint: true },
    },
    guarded("get_run", (a: { run_id: number }) => deps.engine.getRun(a.run_id)),
  );

  // ---------------- write tools ----------------
  server.registerTool(
    "run_checks",
    {
      title: "Run checks now",
      description: "Run all rules for one dataset (or every dataset) immediately.",
      inputSchema: { dataset: z.string().optional() },
    },
    guarded("run_checks", (a: { dataset?: string }) => deps.engine.runChecks(a.dataset)),
  );

  server.registerTool(
    "add_rule",
    {
      title: "Add a rule",
      description: "Add a data-quality rule to a dataset's contract. It runs from the next check onwards.",
      inputSchema: { dataset: z.string(), rule: ruleSchema },
      annotations: { destructiveHint: false, idempotentHint: false },
    },
    guarded("add_rule", (a: { dataset: string; rule: Record<string, unknown> }) =>
      deps.engine.addRule(a.dataset, a.rule, `mcp:${clientName()}`),
    ),
  );

  server.registerTool(
    "annotate_anomaly",
    {
      title: "Annotate a failing result",
      description: "Attach a note (e.g. a suspected cause) to a check result, by result_id.",
      inputSchema: { result_id: z.number().int().positive(), note: z.string().min(1).max(2000) },
    },
    guarded("annotate_anomaly", (a: { result_id: number; note: string }) =>
      deps.engine.annotate(a.result_id, a.note, `mcp:${clientName()}`),
    ),
  );

  return server;
}
