import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import type { Result } from '@/api'
import { plural, timeAgo } from '@/format'

import HealthMark from '../HealthMark.vue'
import RuleStrip from '../RuleStrip.vue'

function result(rule_id: string, severity: Result['severity'], passed: boolean): Result {
  return {
    result_id: 1,
    run_id: 1,
    dataset: 'orders',
    rule_id,
    rule_type: 'freshness',
    severity,
    passed,
    measured_value: null,
    threshold: null,
    message: null,
    sample_rows: [],
    checked_at: new Date().toISOString(),
    annotations: [],
  }
}

describe('HealthMark', () => {
  it.each([
    ['red', 'Failing'],
    ['amber', 'Warning'],
    ['green', 'Healthy'],
    ['unknown', 'Not checked'],
  ] as const)('shows a word for %s, not only a colour', (health, word) => {
    const wrapper = mount(HealthMark, { props: { health } })
    expect(wrapper.text()).toBe(word)
    expect(wrapper.find('svg').exists()).toBe(true)
  })
})

describe('RuleStrip', () => {
  const results = [
    result('low_ok', 'low', true),
    result('crit_fail', 'critical', false),
    result('high_ok', 'high', true),
    result('crit_ok', 'critical', true),
  ]

  it('orders tiles by severity, failing first within a severity', () => {
    const wrapper = mount(RuleStrip, { props: { results } })
    const ids = wrapper.findAll('li').map((li) => li.attributes('data-testid'))
    expect(ids).toEqual(['tile-crit_fail', 'tile-crit_ok', 'tile-high_ok', 'tile-low_ok'])
  })

  it('gives every tile a text label for screen readers', () => {
    const wrapper = mount(RuleStrip, { props: { results } })
    expect(wrapper.find('[data-testid="tile-crit_fail"]').text()).toBe(
      'crit_fail: failing, critical severity',
    )
  })

  it('marks failing tiles with the severity class', () => {
    const wrapper = mount(RuleStrip, { props: { results } })
    expect(wrapper.find('[data-testid="tile-crit_fail"]').classes()).toContain('tile--critical')
    expect(wrapper.find('[data-testid="tile-low_ok"]').classes()).toContain('tile--pass')
  })
})

describe('format', () => {
  it('pluralises', () => {
    expect(plural(1, 'rule')).toBe('1 rule')
    expect(plural(3, 'rule')).toBe('3 rules')
  })

  it('describes time relative to now', () => {
    const now = new Date('2026-10-27T12:00:00Z')
    expect(timeAgo('2026-10-27T11:59:50Z', now)).toBe('just now')
    expect(timeAgo('2026-10-27T11:50:00Z', now)).toBe('10 minutes ago')
    expect(timeAgo('2026-10-24T12:00:00Z', now)).toBe('3 days ago')
    expect(timeAgo(null, now)).toBe('never')
  })
})

import type { LlmCall } from '@/api'
import { percentile, seconds, summarise, usd } from '@/usage'

function call(purpose: string, latency: number, success = true, tin = 100, tout = 10): LlmCall {
  return {
    call_id: 1,
    at: '2026-11-01T10:00:00Z',
    purpose,
    model: 'qwen2.5:3b',
    input_tokens: tin,
    output_tokens: tout,
    cost_usd: '0.000000',
    latency_ms: latency,
    success,
    error: success ? null : 'down',
    investigation_id: 1,
  }
}

describe('AI usage summary', () => {
  it('computes nearest-rank percentiles', () => {
    expect(percentile([], 50)).toBe(0)
    expect(percentile([30, 10, 20], 50)).toBe(20)
    expect(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 100], 95)).toBe(100)
  })

  it('groups calls by step and ignores failed calls for latency', () => {
    const s = summarise([
      call('agent-step', 1000),
      call('agent-step', 3000),
      call('agent-step', 0, false, 0, 0),
      call('agent-answer', 9000, true, 1400, 150),
    ])
    expect(s.calls).toBe(4)
    expect(s.failed).toBe(1)
    expect(s.inputTokens).toBe(1600)
    expect(s.costUsd).toBe(0)
    expect(s.models).toEqual(['qwen2.5:3b'])
    expect(s.byPurpose.map((p) => p.purpose)).toEqual(['agent-step', 'agent-answer'])
    expect(s.byPurpose[0]).toMatchObject({ calls: 3, failed: 1, medianMs: 1000, p95Ms: 3000 })
  })

  it('formats durations and money', () => {
    expect(seconds(240)).toBe('240 ms')
    expect(seconds(41_234)).toBe('41.2 s')
    expect(usd(0)).toBe('$0')
    expect(usd(0.0021)).toBe('$0.0021')
  })
})
