/**
 * Talks to the real MCP server through an in-memory transport, with a fake
 * rules engine and an in-memory audit log. No database or HTTP needed.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { describe, expect, it } from "vitest";

import type { EngineClient } from "./api.js";
import type { AuditEntry, AuditLogger } from "./audit.js";
import { isAllowed, type PermissionConfig } from "./permissions.js";
import { createServer } from "./server.js";

const permissions: PermissionConfig = {
  roles: {
    reader: ["list_failures", "get_dataset", "list_datasets", "get_run"],
    editor: ["list_failures", "get_dataset", "list_datasets", "get_run", "run_checks", "add_rule", "annotate_anomaly"],
  },
};

function fakeEngine(): EngineClient {
  return {
    listFailures: async (p: unknown) => [{ dataset: "orders", rule_id: "orders_fresh", severity: "critical", params: p }],
    listDatasets: async () => [{ dataset: "orders", health: "red" }],
    getDataset: async (name: string) => {
      if (name !== "orders") throw new Error("rules engine GET /datasets/x -> 404");
      return { dataset: "orders" };
    },
    getRun: async (id: number) => ({ run_id: id }),
    runChecks: async () => ({ run_id: 1, status: "failed" }),
    addRule: async (dataset: string, rule: unknown, by: string) => ({ dataset, rule, by }),
    annotate: async (id: number, note: string) => ({ result_id: id, note }),
  } as unknown as EngineClient;
}

async function connect(role: string) {
  const entries: AuditEntry[] = [];
  const audit: AuditLogger = { write: async (e) => void entries.push(e), close: async () => {} };
  const server = createServer({ engine: fakeEngine(), audit, permissions, role, clientName: "test" });
  const [clientT, serverT] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "vitest-client", version: "1.0.0" });
  await Promise.all([server.connect(serverT), client.connect(clientT)]);
  return { client, entries };
}

const text = (r: { content: unknown }) => (r.content as { text: string }[])[0].text;

describe("permissions", () => {
  it("checks role membership", () => {
    expect(isAllowed(permissions, "reader", "list_failures")).toBe(true);
    expect(isAllowed(permissions, "reader", "add_rule")).toBe(false);
    expect(isAllowed(permissions, "ghost", "list_failures")).toBe(false);
  });
});

describe("MCP server", () => {
  it("lists all seven tools", async () => {
    const { client } = await connect("reader");
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual(
      ["add_rule", "annotate_anomaly", "get_dataset", "get_run", "list_datasets", "list_failures", "run_checks"],
    );
  });

  it("reader can read and the call is audited with the client name", async () => {
    const { client, entries } = await connect("reader");
    const res = await client.callTool({ name: "list_failures", arguments: { severity: "critical" } });
    expect(res.isError).toBeFalsy();
    expect(JSON.parse(text(res as never))[0].rule_id).toBe("orders_fresh");
    expect(entries).toEqual([
      expect.objectContaining({ tool: "list_failures", allowed: true, outcome: "ok", client: "vitest-client" }),
    ]);
  });

  it("reader is refused write tools, and the refusal is audited", async () => {
    const { client, entries } = await connect("reader");
    const res = await client.callTool({
      name: "add_rule",
      arguments: { dataset: "orders", rule: { id: "r1", type: "row_count", min: 1 } },
    });
    expect(res.isError).toBe(true);
    expect(text(res as never)).toContain("Permission denied");
    expect(entries[0]).toMatchObject({ tool: "add_rule", allowed: false, outcome: "denied" });
  });

  it("editor can add a rule", async () => {
    const { client, entries } = await connect("editor");
    const res = await client.callTool({
      name: "add_rule",
      arguments: { dataset: "orders", rule: { id: "orders_max", type: "row_count", max: 5 } },
    });
    expect(res.isError).toBeFalsy();
    expect(JSON.parse(text(res as never)).by).toBe("mcp:vitest-client");
    expect(entries[0]).toMatchObject({ outcome: "ok", allowed: true });
  });

  it("engine errors become tool errors and are audited", async () => {
    const { client, entries } = await connect("reader");
    const res = await client.callTool({ name: "get_dataset", arguments: { name: "nope" } });
    expect(res.isError).toBe(true);
    expect(entries[0]).toMatchObject({ outcome: "error", allowed: true });
  });

  it("invalid input is rejected before reaching the engine", async () => {
    const { client, entries } = await connect("editor");
    const res = await client.callTool({ name: "annotate_anomaly", arguments: { result_id: -1, note: "" } });
    expect(res.isError).toBe(true);
    expect(entries).toHaveLength(0);
  });
});
