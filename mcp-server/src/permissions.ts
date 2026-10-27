import { readFileSync } from "node:fs";

export interface PermissionConfig {
  roles: Record<string, string[]>;
}

export function loadPermissions(path: string): PermissionConfig {
  const raw = JSON.parse(readFileSync(path, "utf8")) as PermissionConfig;
  if (!raw.roles || typeof raw.roles !== "object") {
    throw new Error(`${path}: expected a "roles" object`);
  }
  return raw;
}

export function isAllowed(config: PermissionConfig, role: string, tool: string): boolean {
  const allowed = config.roles[role];
  return Array.isArray(allowed) && allowed.includes(tool);
}

export function assertKnownRole(config: PermissionConfig, role: string): void {
  if (!(role in config.roles)) {
    throw new Error(`Unknown role "${role}". Known roles: ${Object.keys(config.roles).join(", ")}`);
  }
}
