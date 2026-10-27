import { expect, test } from '@playwright/test'

test.describe('Overview', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('opens with a sentence saying how many checks fail and where to start', async ({ page }) => {
    const statement = page.getByTestId('statement')
    await expect(statement.getByRole('heading', { level: 1 })).toHaveText(
      /^\d+ of \d+ checks are failing\.$/,
    )
    await expect(statement).toContainText('Start with orders')
  })

  test('shows each dataset with its health in words', async ({ page }) => {
    const orders = page.getByTestId('dataset-orders')
    const customers = page.getByTestId('dataset-customers')
    const products = page.getByTestId('dataset-products')

    await expect(orders.getByTestId('health-red')).toHaveText('Failing')
    await expect(customers.getByTestId('health-red')).toHaveText('Failing')
    await expect(products.getByTestId('health-green')).toHaveText('Healthy')

    // The most broken dataset is listed first.
    await expect(page.getByTestId('dataset-list').locator('li').first()).toHaveAttribute(
      'data-testid',
      'dataset-orders',
    )
  })

  test('the contract strip labels every rule for screen readers', async ({ page }) => {
    const strip = page.getByTestId('dataset-orders').getByTestId('rule-strip')
    await expect(strip.getByTestId('tile-orders_fresh')).toHaveText(
      'orders_fresh: failing, critical severity',
    )
    await expect(strip.getByTestId('tile-orders_min_rows')).toHaveText(
      'orders_min_rows: passing, medium severity',
    )
  })

  test('lists failing rules, most severe first', async ({ page }) => {
    const list = page.getByTestId('failure-list')
    await expect(list.getByTestId('failure-orders_fresh')).toBeVisible()
    await expect(list.getByTestId('failure-orders_unique_id')).toBeVisible()
    await expect(list.getByTestId('failure-customers_email_complete')).toBeVisible()
    await expect(list.getByTestId('failure-orders_schema')).toBeVisible()
    await expect(list.getByTestId('failure-products_unique_id')).toHaveCount(0)

    const severities = await list.locator(':scope > li .sev').allTextContents()
    const rank = { Critical: 0, High: 1, Medium: 2, Low: 3 } as Record<string, number>
    const ranks = severities.map((s) => rank[s.trim()])
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b))
  })

  test('expanding a failure shows the rows that broke the rule', async ({ page }) => {
    const failure = page.getByTestId('failure-orders_unique_id')
    const toggle = failure.getByRole('button', { name: /orders_unique_id/ })

    await expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-expanded', 'true')

    await expect(failure).toContainText('0 duplicate keys')
    const samples = failure.getByTestId('sample-table')
    await expect(samples.getByRole('columnheader', { name: 'order_id' })).toBeVisible()
    await expect(samples.getByRole('columnheader', { name: 'occurrences' })).toBeVisible()
    await expect(samples.locator('tbody tr').first().locator('td').nth(1)).toHaveText('2')

    await toggle.click()
    await expect(samples).toBeHidden()
  })

  test('a note added to a failure is saved', async ({ page }) => {
    const note = `Sales ETL paused — e2e ${Date.now()}`
    const failure = page.getByTestId('failure-orders_fresh')
    await failure.getByRole('button', { name: /orders_fresh/ }).click()

    const save = failure.getByRole('button', { name: 'Save note' })
    await expect(save).toBeDisabled()

    await failure.getByLabel('Add a note').fill(note)
    const response = page.waitForResponse(
      (r) => r.url().includes('/annotations') && r.request().method() === 'POST',
    )
    await save.click()
    expect((await response).status()).toBe(201)

    await expect(failure.getByTestId('notes')).toContainText(note)
    await expect(failure.getByLabel('Add a note')).toHaveValue('')
  })

  test('"Run all checks" runs every contract and reports the result', async ({ page }) => {
    const before = await (await page.request.get('/api/runs?limit=1')).json()

    await page.getByTestId('run-all').click()

    const banner = page.getByTestId('run-result')
    await expect(banner).toHaveText(/Run \d+ finished: \d+ of \d+ checks failing\./)
    const runId = Number((await banner.textContent())!.match(/Run (\d+)/)![1])
    expect(runId).toBeGreaterThan(before[0]?.run_id ?? 0)
    await expect(page.getByTestId('run-all')).toBeEnabled()
  })
})
