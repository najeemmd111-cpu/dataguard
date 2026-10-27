/**
 * Before any test: make sure the rules engine is up and has run every check once,
 * so the dashboard has results to show.
 */
export default async function globalSetup() {
  const engine = process.env.ENGINE_URL ?? 'http://localhost:8000'

  let lastError: unknown
  for (let attempt = 0; attempt < 30; attempt++) {
    try {
      const health = await fetch(`${engine}/health`)
      if (health.ok) {
        const run = await fetch(`${engine}/runs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })
        if (!run.ok) throw new Error(`POST /runs returned ${run.status}`)
        return
      }
    } catch (err) {
      lastError = err
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error(
    `The rules engine at ${engine} is not reachable. Start it with "docker compose up -d" in the repo root. (${lastError})`,
  )
}
