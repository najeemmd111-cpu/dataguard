import type { LlmCall } from './api'

export interface PurposeStats {
  purpose: string
  calls: number
  failed: number
  inputTokens: number
  outputTokens: number
  medianMs: number
  p95Ms: number
}

export interface UsageSummary {
  calls: number
  failed: number
  inputTokens: number
  outputTokens: number
  costUsd: number
  models: string[]
  byPurpose: PurposeStats[]
}

/** Nearest-rank percentile; 0 for an empty list. */
export function percentile(values: number[], p: number): number {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1))
  return sorted[index]!
}

export function summarise(calls: LlmCall[]): UsageSummary {
  const groups = new Map<string, LlmCall[]>()
  for (const c of calls) groups.set(c.purpose, [...(groups.get(c.purpose) ?? []), c])

  const byPurpose: PurposeStats[] = [...groups.entries()]
    .map(([purpose, list]) => {
      const ok = list.filter((c) => c.success)
      const latencies = ok.map((c) => c.latency_ms)
      return {
        purpose,
        calls: list.length,
        failed: list.length - ok.length,
        inputTokens: list.reduce((n, c) => n + c.input_tokens, 0),
        outputTokens: list.reduce((n, c) => n + c.output_tokens, 0),
        medianMs: percentile(latencies, 50),
        p95Ms: percentile(latencies, 95),
      }
    })
    .sort((a, b) => b.calls - a.calls || a.purpose.localeCompare(b.purpose))

  return {
    calls: calls.length,
    failed: calls.filter((c) => !c.success).length,
    inputTokens: calls.reduce((n, c) => n + c.input_tokens, 0),
    outputTokens: calls.reduce((n, c) => n + c.output_tokens, 0),
    costUsd: calls.reduce((n, c) => n + Number(c.cost_usd), 0),
    models: [...new Set(calls.map((c) => c.model))].sort(),
    byPurpose,
  }
}

export function seconds(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`
}

export function tokens(n: number): string {
  return n.toLocaleString('en-GB')
}

export function usd(n: number): string {
  return n === 0 ? '$0' : n < 0.01 ? `$${n.toFixed(4)}` : `$${n.toFixed(2)}`
}
