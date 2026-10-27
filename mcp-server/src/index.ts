#!/usr/bin/env node
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { EngineClient } from "./api.js";
import { createPgAuditLogger } from "./audit.js";
import { assertKnownRole, loadPermissions } from "./permissions.js";
import { createServer } from "./server.js";

const here = dirname(fileURLToPath(import.meta.url));

const config = {
  engineUrl: process.env.ENGINE_URL ?? "http://localhost:8000",
  databaseUrl: process.env.DATABASE_URL ?? "postgresql://dataguard:dataguard@localhost:5432/dataguard",
  role: process.env.MCP_ROLE ?? "reader",
  clientName: process.env.MCP_CLIENT_NAME ?? "unknown-client",
  permissionsPath: process.env.PERMISSIONS_FILE ?? resolve(here, "..", "permissions.json"),
};

async function main() {
  const permissions = loadPermissions(config.permissionsPath);
  assertKnownRole(permissions, config.role);

  const audit = createPgAuditLogger(config.databaseUrl);
  const server = createServer({
    engine: new EngineClient(config.engineUrl),
    audit,
    permissions,
    role: config.role,
    clientName: config.clientName,
  });

  await server.connect(new StdioServerTransport());
  console.error(`[dataguard-mcp] ready (role=${config.role}, engine=${config.engineUrl})`);

  const shutdown = async () => {
    await server.close();
    await audit.close();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  console.error("[dataguard-mcp] fatal:", err);
  process.exit(1);
});
