import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, type TestInfo } from '@playwright/test'

/**
 * Scan the page with axe (WCAG 2.1 A and AA rules) and fail on any
 * serious or critical violation. The full report is attached to the test.
 */
export async function expectAccessible(page: Page, testInfo: TestInfo, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    // The Vue DevTools button only exists in dev mode, not in the product.
    .exclude('#__vue-devtools-container__')
    .exclude('[id^="vue-devtools"]')
    .analyze()

  await testInfo.attach(`axe-${label}.json`, {
    body: JSON.stringify(results.violations, null, 2),
    contentType: 'application/json',
  })

  const serious = results.violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => ({
      rule: v.id,
      impact: v.impact,
      help: v.help,
      nodes: v.nodes.slice(0, 3).map((n) => n.target.join(' ')),
    }))

  expect(serious, `Accessibility problems on ${label}`).toEqual([])
}
