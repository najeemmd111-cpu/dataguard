<script setup lang="ts">
import { computed } from 'vue'

import { api, type DatasetDetail, type DatasetSummary, type Result } from '@/api'
import FailureItem from '@/components/FailureItem.vue'
import HealthMark from '@/components/HealthMark.vue'
import RuleStrip from '@/components/RuleStrip.vue'
import StatusMessage from '@/components/StatusMessage.vue'
import { useAsync } from '@/composables/useAsync'
import { plural, timeAgo } from '@/format'
import { useRefreshStore } from '@/stores/refresh'

interface Overview {
  datasets: DatasetSummary[]
  details: Record<string, DatasetDetail>
  failures: Result[]
}

const refresh = useRefreshStore()

const { data, error, loading, reload } = useAsync<Overview>(async () => {
  const [datasets, failures] = await Promise.all([api.datasets(), api.failures()])
  const details = await Promise.all(datasets.map((d) => api.dataset(d.dataset)))
  return { datasets, failures, details: Object.fromEntries(details.map((d) => [d.dataset, d])) }
})

const healthRank = { red: 0, amber: 1, unknown: 2, green: 3 } as const

const sorted = computed(() =>
  [...(data.value?.datasets ?? [])].sort(
    (a, b) => healthRank[a.health] - healthRank[b.health] || b.failing_rules - a.failing_rules,
  ),
)

const totals = computed(() => {
  const ds = data.value?.datasets ?? []
  const checked = ds.filter((d) => d.last_checked)
  return {
    rules: ds.reduce((n, d) => n + d.rule_count, 0),
    failing: ds.reduce((n, d) => n + d.failing_rules, 0),
    datasets: ds.length,
    anyChecked: checked.length > 0,
  }
})

/** The opening sentence: what's wrong and where to start. */
const statement = computed(() => {
  const t = totals.value
  if (!t.anyChecked)
    return {
      main: 'No checks have run yet.',
      next: 'Run all checks to see how your data holds up against its contracts.',
    }
  if (t.failing === 0)
    return {
      main: `All ${t.rules} checks pass.`,
      next: `${plural(t.datasets, 'dataset')} meet their contracts.`,
    }

  const worst = sorted.value[0]!
  const critical = (data.value?.failures ?? []).filter(
    (f) => f.dataset === worst.dataset && f.severity === 'critical',
  ).length
  const detail = critical ? `, ${critical} of them critical` : ''
  return {
    main: `${t.failing} of ${t.rules} checks are failing.`,
    next: `Start with ${worst.dataset}: ${plural(worst.failing_rules, 'failing rule')}${detail}.`,
  }
})
</script>

<template>
  <div class="page">
    <StatusMessage v-if="loading && !data" kind="loading" />
    <StatusMessage v-else-if="error" kind="error" :message="error" @retry="reload" />

    <template v-else-if="data">
      <header class="statement" data-testid="statement">
        <h1 class="statement__main">{{ statement.main }}</h1>
        <p class="statement__next">{{ statement.next }}</p>
      </header>

      <section class="section" aria-labelledby="contracts-title">
        <h2 id="contracts-title" class="section-title">Contracts</h2>
        <StatusMessage v-if="!sorted.length" kind="empty">
          No contracts found. Add a YAML file to the <code>contracts</code> folder.
        </StatusMessage>
        <ul class="ledger" data-testid="dataset-list">
          <li
            v-for="d in sorted"
            :key="d.dataset"
            class="ledger__row"
            :data-testid="`dataset-${d.dataset}`"
          >
            <div class="ledger__name">
              <RouterLink :to="{ name: 'dataset', params: { name: d.dataset } }">{{
                d.dataset
              }}</RouterLink>
              <span class="ledger__meta">{{ d.table }}, owned by {{ d.owner }}</span>
            </div>
            <RuleStrip :results="data.details[d.dataset]?.latest_results ?? []" />
            <div class="ledger__status">
              <HealthMark :health="d.health" />
              <span class="ledger__meta">
                {{ d.failing_rules }} of {{ d.rule_count }} failing, checked
                {{ timeAgo(d.last_checked) }}
              </span>
            </div>
          </li>
        </ul>
        <p class="legend">
          Each tile is one rule. Taller tiles are more severe; filled, notched tiles are failing.
        </p>
      </section>

      <section class="section" aria-labelledby="failing-title">
        <h2 id="failing-title" class="section-title">Failing now</h2>
        <StatusMessage v-if="!data.failures.length" kind="empty">
          Nothing is failing. New failures will appear here after the next run.
        </StatusMessage>
        <ul v-else class="failures" data-testid="failure-list">
          <FailureItem
            v-for="f in data.failures"
            :key="`${f.result_id}-${refresh.version}`"
            :result="f"
            show-dataset
          />
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.statement {
  max-width: 52rem;
  padding-bottom: var(--space-2);
}

.statement__main {
  font-size: clamp(2rem, 5vw, 3.6rem);
  font-weight: 760;
  font-variation-settings: 'wdth' 118;
  letter-spacing: -0.02em;
  line-height: 1.02;
}

.statement__next {
  margin-top: var(--space-4);
  font-size: var(--step-2);
  font-variation-settings: 'wdth' 96;
  color: var(--ink-muted);
  max-width: 40ch;
}

.ledger {
  margin: 0;
  padding: 0;
  list-style: none;
}

.ledger__row {
  display: grid;
  grid-template-columns: minmax(12rem, 1.2fr) minmax(10rem, 1fr) minmax(14rem, 1fr);
  gap: var(--space-5);
  align-items: end;
  padding: var(--space-5) var(--space-2);
  border-bottom: 1px solid var(--line);
}

.ledger__name a {
  font-size: var(--step-2);
  font-weight: 700;
  font-variation-settings: 'wdth' 108;
  color: var(--ink);
  text-decoration-thickness: 1px;
}

.ledger__name a:hover {
  color: var(--action);
}

.ledger__name,
.ledger__status {
  display: grid;
  gap: var(--space-1);
}

.ledger__meta {
  font-size: var(--step--1);
  color: var(--ink-muted);
  font-variation-settings: 'wdth' 90;
}

.legend {
  margin-top: var(--space-3);
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.failures {
  margin: 0;
  padding: 0;
  list-style: none;
}

code {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 0 0.3em;
}

@media (max-width: 760px) {
  .ledger__row {
    grid-template-columns: 1fr;
    gap: var(--space-3);
    align-items: start;
  }
}
</style>
