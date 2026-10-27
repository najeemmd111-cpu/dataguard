import { expect, test } from '@playwright/test'

test.describe('Dataset page', () => {
  test('opens from the overview and lists every rule in the contract', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('dataset-orders').getByRole('link', { name: 'orders' }).click()

    await expect(page).toHaveURL(/\/datasets\/orders$/)
    await expect(page).toHaveTitle('orders — DataGuard')
    await expect(page.getByRole('heading', { level: 1, name: 'orders' })).toBeVisible()

    const contract = await (await page.request.get('/api/datasets/orders')).json()
    const rows = page.getByTestId('rules-table').locator('tbody tr')
    await expect(rows).toHaveCount(contract.rules.length)

    const fresh = rows.filter({ hasText: 'orders_fresh' })
    await expect(fresh).toContainText('Failing')
    await expect(fresh).toContainText('24h')
  })

  test('runs only this dataset’s checks', async ({ page }) => {
    await page.goto('/datasets/products')
    const runRequest = page.waitForRequest(
      (r) => r.url().endsWith('/api/runs') && r.method() === 'POST',
    )
    await page.getByTestId('run-dataset').click()
    expect((await runRequest).postDataJSON()).toEqual({ dataset: 'products' })
    await expect(page.getByTestId('run-result')).toHaveText(/finished: 0 of \d+ checks failing/)
  })

  test('an unknown dataset explains what happened', async ({ page }) => {
    await page.goto('/datasets/does-not-exist')
    await expect(page.getByTestId('dataset-missing')).toContainText(
      'There is no contract called “does-not-exist”',
    )
    await page.getByRole('link', { name: 'See all contracts' }).click()
    await expect(page).toHaveURL(/\/$/)
  })
})

test.describe('Run history', () => {
  test('shows the latest runs, newest first, with a chart', async ({ page }) => {
    await page.goto('/runs')
    await expect(page.getByRole('img', { name: /Failed rules per run/ })).toBeVisible()

    const ids = (await page.getByTestId('runs-table').locator('tbody tr td:first-child').allTextContents()).map(Number)
    expect(ids.length).toBeGreaterThan(0)
    expect(ids).toEqual([...ids].sort((a, b) => b - a))
  })
})

test.describe('AI access log', () => {
  const entries = [
    { audit_id: 3, at: '2026-10-27T16:47:13Z', client: 'mcp-inspector', role: 'editor', tool: 'add_rule',
      arguments: { dataset: 'orders' }, allowed: true, outcome: 'ok', detail: null },
    { audit_id: 2, at: '2026-10-27T16:45:43Z', client: 'mcp-inspector', role: 'reader', tool: 'add_rule',
      arguments: { dataset: 'orders' }, allowed: false, outcome: 'denied', detail: 'role lacks permission' },
    { audit_id: 1, at: '2026-10-27T16:38:15Z', client: 'mcp-inspector', role: 'reader', tool: 'list_failures',
      arguments: { severity: 'critical' }, allowed: true, outcome: 'ok', detail: null },
  ]

  test('filters calls into allowed and refused', async ({ page }) => {
    // The audit log is written by the MCP server, so give the page a known log.
    await page.route('**/api/audit*', (route) => route.fulfill({ json: entries }))
    await page.goto('/audit')

    const rows = page.getByTestId('audit-table').locator('tbody tr')
    await expect(rows).toHaveCount(3)

    await page.getByLabel(/Refused \(1\)/).check()
    await expect(rows).toHaveCount(1)
    await expect(rows.first()).toContainText('Refused')
    await expect(rows.first()).toContainText('role lacks permission')
    await expect(rows.first()).toContainText('reader')

    await page.getByLabel(/Allowed \(2\)/).check()
    await expect(rows).toHaveCount(2)
    await expect(rows.filter({ hasText: 'Refused' })).toHaveCount(0)
  })

  test('explains what to do when no AI client has connected yet', async ({ page }) => {
    await page.route('**/api/audit*', (route) => route.fulfill({ json: [] }))
    await page.goto('/audit')
    await expect(page.getByTestId('status-empty')).toContainText('Connect an MCP client')
  })
})
