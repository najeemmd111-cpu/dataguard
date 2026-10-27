# End-to-end tests (Phase 2) — Playwright + axe

```bash
cd e2e
npm init playwright@latest .        # TypeScript, tests folder "tests", add GitHub Actions: no (already in ci.yml)
npm install -D @axe-core/playwright
```

In `playwright.config.ts`: `reporter: [['html', { open: 'never' }]]`, `use: { baseURL: 'http://localhost:5173', trace: 'retain-on-failure', screenshot: 'only-on-failure' }`.

## Tests to write (8–12)

1. Overview lists `orders`, `customers`, `products` with the right health
2. Filter failures by severity
3. Open `orders` and see the freshness failure with its sample row
4. Add an annotation and see it appear
5. Empty state (dataset with no results yet)
6. API error state (use `page.route` to return 500)
7. Audit page shows denied calls
8. Keyboard-only navigation from overview to a dataset

## Axe check (one per page)

```ts
import AxeBuilder from '@axe-core/playwright';

const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
const serious = results.violations.filter(v => ['serious', 'critical'].includes(v.impact ?? ''));
expect(serious).toEqual([]);
```

Then uncomment the `e2e` job in `.github/workflows/ci.yml`.
