import { defineConfig, devices } from '@playwright/test'

/**
 * Runs against the real stack:
 *   - rules engine + Postgres: `docker compose up -d` in the repo root (port 8000)
 *   - dashboard: started below with `npm run dev` (port 5173), or reused if already running
 */
const DASHBOARD_URL = process.env.DASHBOARD_URL ?? 'http://localhost:5173'
const isCI = !!process.env.CI

export default defineConfig({
  testDir: './tests',
  globalSetup: './global-setup.ts',
  // Tests share one database, and some run checks or add notes; run them one at a time.
  workers: 1,
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: DASHBOARD_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // Only needed where Playwright's own browser can't be installed.
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], colorScheme: 'light' } },
    {
      name: 'mobile-dark',
      use: { ...devices['Pixel 7'], colorScheme: 'dark' },
      // On a phone in dark mode, re-run only the accessibility scans.
      grep: /@a11y/,
    },
  ],
  webServer: {
    command: 'npm run dev -- --port 5173 --strictPort',
    cwd: '../dashboard',
    url: DASHBOARD_URL,
    reuseExistingServer: !isCI,
    timeout: 60_000,
  },
})
