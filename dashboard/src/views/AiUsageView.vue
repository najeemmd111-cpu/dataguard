<script setup lang="ts">
import { computed } from 'vue'

import { api, type Investigation, type LlmCall } from '@/api'
import StatusMessage from '@/components/StatusMessage.vue'
import { useAsync } from '@/composables/useAsync'
import { dateTime } from '@/format'
import { seconds, summarise, tokens, usd } from '@/usage'

const { data, error, loading, reload } = useAsync<{
  calls: LlmCall[]
  investigations: Investigation[]
}>(async () => {
  const [calls, investigations] = await Promise.all([
    api.llmCalls(1000),
    api.investigations({ limit: 10 }),
  ])
  return { calls, investigations }
})

const summary = computed(() => summarise(data.value?.calls ?? []))
</script>

<template>
  <div class="page">
    <h1 class="page-title">AI usage</h1>
    <p class="lede">
      Every call the root-cause agent makes to a language model: tokens, response time and cost. The
      latest 1,000 calls are included.
    </p>

    <StatusMessage v-if="loading && !data" kind="loading" />
    <StatusMessage v-else-if="error" kind="error" :message="error" @retry="reload" />
    <StatusMessage v-else-if="!data?.calls.length" kind="empty">
      No model calls yet. Ask the agent to explain a failure:
      <code>docker compose run --rm agent investigate orders_fresh</code>
    </StatusMessage>

    <template v-else>
      <dl class="totals" data-testid="usage-totals">
        <div>
          <dt>Model calls</dt>
          <dd>{{ tokens(summary.calls) }}</dd>
        </div>
        <div>
          <dt>Tokens in / out</dt>
          <dd>{{ tokens(summary.inputTokens) }} / {{ tokens(summary.outputTokens) }}</dd>
        </div>
        <div>
          <dt>Cost</dt>
          <dd>{{ usd(summary.costUsd) }}</dd>
        </div>
        <div>
          <dt>Failed calls</dt>
          <dd :class="{ bad: summary.failed > 0 }">{{ summary.failed }}</dd>
        </div>
      </dl>
      <p class="models">
        Models: {{ summary.models.join(', ') }}. Local models cost nothing per call.
      </p>

      <section class="section" aria-labelledby="purpose-title">
        <h2 id="purpose-title" class="section-title">By step</h2>
        <div class="table-scroll" tabindex="0" role="region" aria-label="Model calls by step">
          <table class="data-table" data-testid="usage-by-purpose">
            <thead>
              <tr>
                <th scope="col">Step</th>
                <th scope="col" class="num">Calls</th>
                <th scope="col" class="num">Failed</th>
                <th scope="col" class="num">Tokens in</th>
                <th scope="col" class="num">Tokens out</th>
                <th scope="col" class="num">Median time</th>
                <th scope="col" class="num">p95 time</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in summary.byPurpose" :key="p.purpose">
                <th scope="row">{{ p.purpose }}</th>
                <td class="num">{{ p.calls }}</td>
                <td class="num">{{ p.failed }}</td>
                <td class="num">{{ tokens(p.inputTokens) }}</td>
                <td class="num">{{ tokens(p.outputTokens) }}</td>
                <td class="num">{{ seconds(p.medianMs) }}</td>
                <td class="num">{{ seconds(p.p95Ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="note">
          <strong>agent-step</strong> calls decide which tool to use next;
          <strong>agent-answer</strong> calls write the final structured answer.
        </p>
      </section>

      <section class="section" aria-labelledby="inv-title">
        <h2 id="inv-title" class="section-title">Recent investigations</h2>
        <div class="table-scroll" tabindex="0" role="region" aria-label="Recent investigations">
          <table class="data-table" data-testid="investigations-table">
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Rule</th>
                <th scope="col">Outcome</th>
                <th scope="col" class="num">Tool calls</th>
                <th scope="col" class="num">Tokens</th>
                <th scope="col" class="num">Time</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in data.investigations" :key="i.investigation_id">
                <td>{{ dateTime(i.created_at) }}</td>
                <th scope="row">
                  <RouterLink :to="{ name: 'dataset', params: { name: i.dataset } }">{{
                    i.dataset
                  }}</RouterLink>
                  / {{ i.rule_id }}
                </th>
                <td :class="i.status === 'ok' ? 'good' : 'bad'">
                  {{
                    i.status === 'ok' ? 'Explained' : i.status === 'running' ? 'Running' : 'Failed'
                  }}
                  <span v-if="i.error" class="detail">{{ i.error }}</span>
                </td>
                <td class="num">{{ i.tool_calls }}</td>
                <td class="num">{{ tokens(i.input_tokens + i.output_tokens) }}</td>
                <td class="num">{{ seconds(i.latency_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.totals {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4) var(--space-6);
  margin: var(--space-6) 0 var(--space-2);
}

.totals dt {
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.totals dd {
  margin: 0;
  font-size: var(--step-2);
  font-weight: 700;
  font-variation-settings: 'wdth' 100;
}

.models,
.note {
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.note {
  margin-top: var(--space-3);
}

.good {
  color: var(--pass);
  font-weight: 600;
}

.bad {
  color: var(--critical);
  font-weight: 600;
}

.detail {
  display: block;
  font-weight: 400;
  color: var(--ink-muted);
}

code {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 0 0.3em;
}
</style>
