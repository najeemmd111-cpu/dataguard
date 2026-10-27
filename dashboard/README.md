# Dashboard (Phase 2) — Vue 3

Not built yet. Start with:

```bash
cd dashboard
npm create vue@latest .     # choose: TypeScript, Vue Router, Pinia, Vitest, ESLint
npm install
npm run dev                 # http://localhost:5173 (already allowed by the engine's CORS)
```

## Pages to build

| Route | Data source | Notes |
|---|---|---|
| `/` Overview | `GET /datasets` | health badge per dataset: icon + text + colour (never colour alone) |
| `/datasets/:name` | `GET /datasets/{name}` | rules, latest results, sample rows, annotations; form to add an annotation |
| `/runs` | `GET /runs` | chart of failed rules over time |
| `/audit` | `GET /audit` | table of MCP calls, filter by allowed/denied |
| `/costs` (phase 3) | `GET /llm-calls` | cost per day, avg/p95 latency per purpose |

## Accessibility checklist

- Semantic elements (`<main>`, `<nav>`, `<table>` with `<th scope>`), one `<h1>` per page
- Every input has a `<label>`; errors announced with `aria-live="polite"`
- Visible focus styles; everything reachable by keyboard
- Add `data-testid` attributes now — Playwright tests will use them
