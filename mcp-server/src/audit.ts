import pg from "pg";

export interface AuditEntry {
  client: string;
  role: string;
  tool: string;
  args: unknown;
  allowed: boolean;
  outcome: "ok" | "denied" | "error";
  detail?: string;
}

export interface AuditLogger {
  write(entry: AuditEntry): Promise<void>;
  close(): Promise<void>;
}

/** Writes one row per tool call into dq.audit_log. Never throws into the tool call. */
export function createPgAuditLogger(databaseUrl: string): AuditLogger {
  const pool = new pg.Pool({ connectionString: databaseUrl, max: 2 });
  return {
    async write(e) {
      try {
        await pool.query(
          `INSERT INTO dq.audit_log (client, role, tool, arguments, allowed, outcome, detail)
           VALUES ($1, $2, $3, $4, $5, $6, $7)`,
          [e.client, e.role, e.tool, JSON.stringify(e.args ?? {}), e.allowed, e.outcome, e.detail ?? null],
        );
      } catch (err) {
        // stdout belongs to the MCP protocol: log to stderr only.
        console.error("[dataguard-mcp] audit write failed:", (err as Error).message);
      }
    },
    close: () => pool.end(),
  };
}
