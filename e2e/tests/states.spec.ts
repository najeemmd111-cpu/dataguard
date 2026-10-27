import { expect, test } from '@playwright/test'

test.describe('Error and empty states', () => {
  test('tells the user how to start the engine when it is down, and recovers', async ({ page }) => {
    // Simulate Vite's proxy failing to reach the engine (a non-JSON 502).
    let engineDown = true
    await page.route('**/api/**', (route) =>
      engineDown
        ? route.fulfill({ status: 502, contentType: 'text/plain', body: 'Bad Gateway' })
        : route.fallback(),
    )

    await page.goto('/')
    const error = page.getByTestId('status-error')
    await expect(error).toContainText('The rules engine is not reachable.')
    await expect(error).toContainText('docker compose up -d')

    engineDown = false
    await error.getByRole('button', { name: 'Try again' }).click()
    await expect(page.getByTestId('statement')).toBeVisible()
  })

  test('shows when nothing is failing', async ({ page }) => {
    await page.route('**/api/failures*', (route) => route.fulfill({ json: [] }))
    await page.goto('/')
    await expect(page.getByTestId('failure-list')).toHaveCount(0)
    await expect(page.getByText('Nothing is failing.')).toBeVisible()
  })

  test('shows when no checks have run yet', async ({ page }) => {
    await page.route('**/api/datasets', async (route) => {
      const datasets = await (await route.fetch()).json()
      await route.fulfill({
        json: datasets.map((d: object) => ({ ...d, last_checked: null, health: 'unknown', failing_rules: 0 })),
      })
    })
    await page.route('**/api/failures*', (route) => route.fulfill({ json: [] }))
    await page.goto('/')
    await expect(page.getByTestId('statement')).toContainText('No checks have run yet.')
    await expect(page.getByTestId('health-unknown')).toHaveCount(3)
  })

  test('reports a failed run instead of hiding it', async ({ page }) => {
    await page.goto('/')
    await page.route('**/api/runs', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, json: { detail: 'database is read-only' } })
        : route.fallback(),
    )
    await page.getByTestId('run-all').click()
    await expect(page.getByRole('alert')).toHaveText('Checks could not run: database is read-only')
  })

  test('unknown pages say so', async ({ page }) => {
    await page.goto('/no/such/page')
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('This page doesn’t exist')
  })
})

test.describe('Keyboard', () => {
  test('skip link jumps to the main content', async ({ page }) => {
    await page.goto('/')
    await page.keyboard.press('Tab')
    const skip = page.getByRole('link', { name: 'Skip to content' })
    await expect(skip).toBeFocused()
    await expect(skip).toBeInViewport()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/#main$/)
  })

  test('a failure can be opened and annotated without a mouse', async ({ page }) => {
    await page.goto('/')
    const toggle = page.getByTestId('failure-customers_email_complete').getByRole('button').first()
    await toggle.focus()
    await page.keyboard.press('Enter')
    await expect(toggle).toHaveAttribute('aria-expanded', 'true')

    // Focus moves into the details: the sample table (scrollable, so focusable), then the note field.
    const failure = page.getByTestId('failure-customers_email_complete')
    await page.keyboard.press('Tab')
    await expect(failure.getByRole('region', { name: 'Sample rows for customers_email_complete' })).toBeFocused()
    await page.keyboard.press('Tab')
    await expect(failure.getByTestId('note-input')).toBeFocused()
    await page.keyboard.type('Owner notified')
    await page.keyboard.press('Enter')
    await expect(failure.getByTestId('notes')).toContainText('Owner notified')
  })

  test('main navigation works with Tab and Enter', async ({ page }) => {
    await page.goto('/')
    const runHistory = page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Run history' })
    await runHistory.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/runs$/)
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Run history')
  })
})
