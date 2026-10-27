/** Typed client for the DataGuard rules engine (proxied at /api by Vite). */

export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Health = 'red' | 'amber' | 'green' | 'unknown'

export interface Annotation {
  annotation_id: number
  result_id: number
  note: string
  author: string
  created_at: string
}

export interface Result {
  result_id: number
  run_id: number
  dataset: string
  rule_id: string
  rule_type: string
  severity: Severity
  passed: boolean
  measured_value: string | null
  threshold: string | null
  message: string | null
  sample_rows: Record<string, unknown>[]
  checked_at: string
  annotations: Annotation[]
}

export interface DatasetSummary {
  dataset: string
  table: string
  owner: string
  description: string | null
  schedule: string | null
  rule_count: number
  failing_rules: number
  last_checked: string | null
  health: Health
}

export interface RuleSpec {
  id: string
  type: string
  severity: Severity
  description?: string | null
}

export interface DatasetDetail {
  dataset: string
  table: string
  owner: string
  description: string | null
  schedule: string | null
  rules: RuleSpec[]
  latest_results: Result[]
  health: Health
}

export interface Run {
  run_id: number
  trigger: string
  dataset: string | null
  started_at: string
  finished_at: string | null
  status: 'running' | 'passed' | 'failed' | 'error'
  total_rules: number
  failed_rules: number
}

export interface AuditEntry {
  audit_id: number
  at: string
  client: string
  role: string
  tool: string
  arguments: Record<string, unknown>
  allowed: boolean
  outcome: 'ok' | 'denied' | 'error'
  detail: string | null
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'The rules engine is not reachable.')
  }
  if (!res.ok) {
    let body: { detail?: unknown } | null = null
    try {
      body = await res.json()
    } catch {
      /* not JSON */
    }
    // The engine always answers errors in JSON. A non-JSON 5xx comes from
    // Vite's proxy, which means the engine is down.
    if (res.status >= 500 && body === null) {
      throw new ApiError(res.status, 'The rules engine is not reachable.')
    }
    const detail =
      typeof body?.detail === 'string'
        ? body.detail
        : body?.detail
          ? JSON.stringify(body.detail)
          : ''
    throw new ApiError(res.status, detail || `Request failed (${res.status})`)
  }
  return (await res.json()) as T
}

export const api = {
  datasets: () => request<DatasetSummary[]>('/datasets'),
  dataset: (name: string) => request<DatasetDetail>(`/datasets/${encodeURIComponent(name)}`),
  failures: (params: { severity?: Severity; dataset?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.severity) q.set('severity', params.severity)
    if (params.dataset) q.set('dataset', params.dataset)
    const qs = q.toString()
    return request<Result[]>(`/failures${qs ? `?${qs}` : ''}`)
  },
  runs: (limit = 50) => request<Run[]>(`/runs?limit=${limit}`),
  audit: (limit = 200) => request<AuditEntry[]>(`/audit?limit=${limit}`),
  runChecks: (dataset?: string) =>
    request<Run>('/runs', { method: 'POST', body: JSON.stringify({ dataset: dataset ?? null }) }),
  annotate: (resultId: number, note: string) =>
    request<Annotation>(`/results/${resultId}/annotations`, {
      method: 'POST',
      body: JSON.stringify({ note, author: 'dashboard' }),
    }),
}
