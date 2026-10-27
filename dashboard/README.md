# DataGuard dashboard (Vue 3)

Shows each dataset's contract health, what is failing and why, run history, and every AI tool call made through the MCP server.

## Run

The rules engine must be running (`docker compose up -d` in the repo root).

```bash
npm install
npm run dev          # http://localhost:5173
```

The dashboard calls `/api/...`; Vite forwards that to the engine at `http://localhost:8000`.
If your engine runs on another port: `ENGINE_URL=http://localhost:8001 npm run dev`.

## Pages

| Route | What it shows |
|---|---|
| `/` | One-sentence summary, a contract strip per dataset, and every failing rule (expand for sample rows and notes) |
| `/datasets/:name` | The contract's rules with measured vs allowed values; run that dataset's checks |
| `/runs` | Failed vs checked rules per run, and the run table |
| `/audit` | MCP tool calls: client, role, arguments, allowed or refused |

## The contract strip

Each tile is one rule, most severe on the left. Tile height is severity (critical tallest); outlined tiles pass, filled notched tiles fail. Health is always shown with an icon and a word too, never colour alone.

## Checks

```bash
npm run test:unit -- --run   # component tests (Vitest)
npm run build                # type-check + production build
npm run lint
```

Elements that end-to-end tests need carry `data-testid` attributes (`run-all`, `dataset-orders`, `failure-orders_fresh`, `note-input`, `filter-denied`, …).
