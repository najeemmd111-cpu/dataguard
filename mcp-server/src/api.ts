/** Thin client for the rules-engine HTTP API. */

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export class EngineClient {
  constructor(private baseUrl: string) {}

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(new URL(path, this.baseUrl), {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(60_000),
    });
    const text = await res.text();
    if (!res.ok) {
      let detail = text;
      try {
        detail = JSON.stringify(JSON.parse(text).detail ?? text);
      } catch {
        /* keep raw text */
      }
      throw new ApiError(res.status, `rules engine ${method} ${path} -> ${res.status}: ${detail}`);
    }
    return (text ? JSON.parse(text) : null) as T;
  }

  listFailures(params: { severity?: string; dataset?: string; limit?: number }) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined) q.set(k, String(v));
    return this.request<unknown[]>("GET", `/failures?${q}`);
  }
  listDatasets() {
    return this.request<unknown[]>("GET", "/datasets");
  }
  getDataset(name: string) {
    return this.request<unknown>("GET", `/datasets/${encodeURIComponent(name)}`);
  }
  getRun(id: number) {
    return this.request<unknown>("GET", `/runs/${id}`);
  }
  runChecks(dataset?: string) {
    return this.request<unknown>("POST", "/runs", { dataset: dataset ?? null });
  }
  addRule(dataset: string, rule: Record<string, unknown>, createdBy: string) {
    return this.request<unknown>("POST", "/rules", { dataset, rule, created_by: createdBy });
  }
  annotate(resultId: number, note: string, author: string) {
    return this.request<unknown>("POST", `/results/${resultId}/annotations`, { note, author });
  }
}
