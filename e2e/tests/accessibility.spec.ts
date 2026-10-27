import { expect, test } from '@playwright/test'

import { expectAccessible } from './helpers'

/**
 * axe scans of every page. Tagged @a11y so the mobile-dark project repeats
 * them on a phone-sized screen in dark mode (contrast differs per theme).
 */
test.describe('Accessibility @a11y', () => {
  test('overview', async ({ page }, testInfo) => {
    await page.goto('/')
    await expect(page.getByTestId('statement')).toBeVisible()
    await expectAccessible(page, testInfo, 'overview')
  })

  test('overview with a failure expanded', async ({ page }, testInfo) => {
    await page.goto('/')
    await page.getByTestId('failure-orders_unique_id').getByRole('button').first().click()
    await expect(page.getByTestId('sample-table')).toBeVisible()
    await expectAccessible(page, testInfo, 'overview-expanded')
  })

  test('dataset page', async ({ page }, testInfo) => {
    await page.goto('/datasets/orders')
    await expect(page.getByTestId('rules-table')).toBeVisible()
    await expectAccessible(page, testInfo, 'dataset')
  })

  test('run history', async ({ page }, testInfo) => {
    await page.goto('/runs')
    await expect(page.getByTestId('runs-table')).toBeVisible()
    await expectAccessible(page, testInfo, 'runs')
  })

  test('AI access log', async ({ page }, testInfo) => {
    await page.route('**/api/audit*', (route) =>
      route.fulfill({
        json: [
          { audit_id: 2, at: '2026-10-27T16:45:43Z', client: 'mcp-inspector', role: 'reader', tool: 'add_rule',
            arguments: { dataset: 'orders' }, allowed: false, outcome: 'denied', detail: 'role lacks permission' },
          { audit_id: 1, at: '2026-10-27T16:38:15Z', client: 'mcp-inspector', role: 'reader', tool: 'list_failures',
            arguments: { severity: 'critical' }, allowed: true, outcome: 'ok', detail: null },
        ],
      }),
    )
    await page.goto('/audit')
    await expect(page.getByTestId('audit-table')).toBeVisible()
    await expectAccessible(page, testInfo, 'audit')
  })

  test('error state', async ({ page }, testInfo) => {
    await page.route('**/api/**', (route) =>
      route.fulfill({ status: 502, contentType: 'text/plain', body: 'Bad Gateway' }),
    )
    await page.goto('/')
    await expect(page.getByTestId('status-error')).toBeVisible()
    await expectAccessible(page, testInfo, 'error')
  })
})
