import { expect, test, type Page } from '@playwright/test'

import { expectAccessible } from './helpers'

/**
 * The agent itself needs a local language model, so these tests give the dashboard
 * fixed investigations and model calls through page.route.
 */
const investigation = {
  investigation_id: 7,
  created_at: '2026-11-01T17:40:00Z',
  dataset: 'orders',
  rule_id: 'orders_fresh',
  result_id: 13,
  model: 'qwen2.5:3b',
  status: 'ok',
  answer: {
    summary: 'The sales ETL stopped three days ago, so no new orders have arrived.',
    likely_cause: 'The sales ETL job is not running.',
    evidence: ['Newest updated_at is 72.4 hours old; 24 hours allowed', 'Failing in the last 9 checks'],
    fix_steps: ['Restart the sales ETL job', 'Run a catch-up load for the missing days', 'Re-run the orders checks'],
    confidence: 'medium',
    sources: ['runbook-orders#orders-fresh-fails', 'late-etl-jobs#how-to-confirm-it'],
  },
  tool_calls: 2,
  input_tokens: 4700,
  output_tokens: 205,
  latency_ms: 41_200,
  error: null,
}

const calls = [
  { purpose: 'agent-step', latency: 9_000, ok: true, tin: 1200, tout: 25 },
  { purpose: 'agent-step', latency: 11_000, ok: true, tin: 1500, tout: 20 },
  { purpose: 'agent-step', latency: 0, ok: false, tin: 0, tout: 0 },
  { purpose: 'agent-answer', latency: 21_000, ok: true, tin: 2000, tout: 160 },
].map((c, i) => ({
  call_id: i + 1,
  at: '2026-11-01T17:40:00Z',
  purpose: c.purpose,
  model: 'qwen2.5:3b',
  input_tokens: c.tin,
  output_tokens: c.tout,
  cost_usd: '0.000000',
  latency_ms: c.latency,
  success: c.ok,
  error: c.ok ? null : 'Cannot reach Ollama at http://localhost:11434',
  investigation_id: 7,
}))

async function mockAgentData(page: Page, opts: { explained: boolean }) {
  await page.route('**/api/investigations?*', (route) => {
    const url = new URL(route.request().url())
    const ruleId = url.searchParams.get('rule_id')
    const match = opts.explained && (!ruleId || ruleId === 'orders_fresh')
    return route.fulfill({ json: match ? [investigation] : [] })
  })
  await page.route('**/api/llm-calls*', (route) => route.fulfill({ json: calls }))
}

test.describe('AI explanations', () => {
  test('a failure shows the latest explanation from the agent', async ({ page }) => {
    await mockAgentData(page, { explained: true })
    await page.goto('/')
    const failure = page.getByTestId('failure-orders_fresh')
    await failure.getByRole('button', { name: /orders_fresh/ }).click()

    const ai = failure.getByTestId('ai-orders_fresh')
    await expect(ai.getByRole('heading', { name: 'AI explanation' })).toBeVisible()
    await expect(ai).toContainText('The sales ETL stopped three days ago')
    await expect(ai.getByRole('listitem')).toHaveCount(5) // 2 evidence + 3 fix steps
    await expect(ai).toContainText('runbook-orders#orders-fresh-fails')
    await expect(ai).toContainText('Confidence: medium. qwen2.5:3b, 2 tool calls, 41.2 s')
    await expect(ai).toContainText('check the evidence before acting')
  })

  test('a warning is shown when the answer claims something the agent cannot do', async ({ page }) => {
    const flagged = {
      ...investigation,
      answer: {
        ...investigation.answer,
        confidence: 'low',
        warnings: ['This answer claims an action the agent cannot take (it can only read data): "executed successfully".'],
      },
    }
    await page.route('**/api/investigations?*', (route) => route.fulfill({ json: [flagged] }))
    await page.goto('/')
    const failure = page.getByTestId('failure-orders_fresh')
    await failure.getByRole('button', { name: /orders_fresh/ }).click()
    await expect(failure.getByTestId('ai-warning')).toContainText('it can only read data')
    await expect(failure.getByTestId('ai-orders_fresh')).toContainText('Confidence: low')
  })

  test('a failure without an explanation says how to ask for one', async ({ page }) => {
    await mockAgentData(page, { explained: true })
    await page.goto('/')
    const failure = page.getByTestId('failure-orders_unique_id')
    await failure.getByRole('button', { name: /orders_unique_id/ }).click()
    await expect(failure.getByTestId('ai-none')).toContainText(
      'docker compose run --rm agent investigate orders_unique_id',
    )
  })
})

test.describe('AI usage page', () => {
  test('summarises model calls by step', async ({ page }) => {
    await mockAgentData(page, { explained: true })
    await page.goto('/')
    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'AI usage' }).click()
    await expect(page).toHaveURL(/\/ai-usage$/)
    await expect(page).toHaveTitle('AI usage — DataGuard')

    const totals = page.getByTestId('usage-totals')
    await expect(totals).toContainText('4') // calls
    await expect(totals).toContainText('4,700 / 205')
    await expect(totals).toContainText('$0')

    const rows = page.getByTestId('usage-by-purpose').locator('tbody tr')
    await expect(rows).toHaveCount(2)
    const step = rows.filter({ hasText: 'agent-step' })
    await expect(step).toContainText('3') // calls
    await expect(step).toContainText('9.0 s') // median of the successful calls
    await expect(step).toContainText('11.0 s') // p95

    const inv = page.getByTestId('investigations-table').locator('tbody tr')
    await expect(inv).toHaveCount(1)
    await expect(inv.first()).toContainText('Explained')
  })

  test('explains how to start when there are no calls yet', async ({ page }) => {
    await page.route('**/api/investigations?*', (route) => route.fulfill({ json: [] }))
    await page.route('**/api/llm-calls*', (route) => route.fulfill({ json: [] }))
    await page.goto('/ai-usage')
    await expect(page.getByTestId('status-empty')).toContainText('docker compose run --rm agent investigate')
  })
})

test.describe('Accessibility of AI views @a11y', () => {
  test('AI usage page', async ({ page }, testInfo) => {
    await mockAgentData(page, { explained: true })
    await page.goto('/ai-usage')
    await expect(page.getByTestId('usage-by-purpose')).toBeVisible()
    await expectAccessible(page, testInfo, 'ai-usage')
  })

  test('failure with an AI explanation', async ({ page }, testInfo) => {
    await mockAgentData(page, { explained: true })
    await page.goto('/')
    await page.getByTestId('failure-orders_fresh').getByRole('button').first().click()
    await expect(page.getByTestId('ai-orders_fresh')).toContainText('likely cause', { ignoreCase: true })
    await expectAccessible(page, testInfo, 'ai-explanation')
  })
})
