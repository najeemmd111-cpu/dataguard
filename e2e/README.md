# End-to-end tests — Playwright + axe

33 tests that drive a real browser through the whole stack: Postgres → rules engine → dashboard.

| File | What it covers |
|---|---|
| `tests/overview.spec.ts` | Summary sentence, dataset health, contract strip labels, failure order, expanding a failure, saving a note, running all checks |
| `tests/pages.spec.ts` | Dataset page, running one dataset's checks, unknown dataset, run history, AI access log filters |
| `tests/states.spec.ts` | Engine down (and recovery), nothing failing, no runs yet, failed run, unknown page, keyboard-only use |
| `tests/accessibility.spec.ts` | axe scan (WCAG 2.1 A/AA) of every page; fails on serious or critical issues |

The accessibility scans run twice: on a desktop in light mode, and on a phone-sized screen in dark mode, because contrast and layout differ.

Tests that need data the engine can't produce on demand (the MCP audit log, an empty or broken engine) replace the API response with `page.route`. Everything else uses the real engine and database.

## Run locally

```bash
# 1. In the repo root: database, seed data and rules engine
docker compose up -d

# 2. Once
cd e2e
npm install
npx playwright install chromium

# 3. Run (starts the dashboard itself, or reuses one already on :5173)
npm test
npm run report        # open the HTML report
npm run test:ui       # interactive mode, good for debugging
```

## In CI

The `e2e` job in `.github/workflows/ci.yml` starts the stack with Docker Compose, runs the suite, and uploads the HTML report as the `playwright-report` artifact (Actions → the run → Artifacts). Traces and screenshots are kept for any failed test.

## What it found

The first axe run on the phone-sized screen caught a real problem: wide tables scrolled sideways, but keyboard users could not reach the scroll area (`scrollable-region-focusable`). The table wrappers are now focusable regions with labels.
