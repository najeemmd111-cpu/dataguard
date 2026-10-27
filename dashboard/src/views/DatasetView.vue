<script setup lang="ts">
import { computed } from 'vue'

import { api, ApiError } from '@/api'
import FailureItem from '@/components/FailureItem.vue'
import HealthMark from '@/components/HealthMark.vue'
import RuleStrip from '@/components/RuleStrip.vue'
import SeverityTag from '@/components/SeverityTag.vue'
import StatusMessage from '@/components/StatusMessage.vue'
import { useAsync } from '@/composables/useAsync'
import { SEVERITY_ORDER, timeAgo } from '@/format'
import { useRefreshStore } from '@/stores/refresh'

const props = defineProps<{ name: string }>()
const refresh = useRefreshStore()

const { data, error, loading, reload } = useAsync(async () => {
  try {
    return await api.dataset(props.name)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}, [() => props.name])

const failing = computed(() =>
  (data.value?.latest_results ?? [])
    .filter((r) => !r.passed)
    .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)),
)

const rows = computed(() => {
  const results = new Map((data.value?.latest_results ?? []).map((r) => [r.rule_id, r]))
  return (data.value?.rules ?? []).map((rule) => ({ rule, result: results.get(rule.id) }))
})
</script>

<template>
  <div class="page">
    <RouterLink class="back" :to="{ name: 'overview' }">All contracts</RouterLink>

    <StatusMessage v-if="loading && !data" kind="loading" />
    <StatusMessage v-else-if="error" kind="error" :message="error" @retry="reload" />
    <StatusMessage v-else-if="data === null" kind="empty" data-testid="dataset-missing">
      There is no contract called “{{ name }}”.
      <RouterLink :to="{ name: 'overview' }">See all contracts</RouterLink>.
    </StatusMessage>

    <template v-else-if="data">
      <header class="head">
        <div>
          <h1 class="page-title">{{ data.dataset }}</h1>
          <p class="lede">
            {{ data.description || 'No description in the contract.' }}
          </p>
          <p class="meta">
            Table <strong>{{ data.table }}</strong
            >, owned by <strong>{{ data.owner }}</strong
            ><template v-if="data.schedule"
              >, checked on schedule <strong>{{ data.schedule }}</strong></template
            >
          </p>
        </div>
        <div class="head__side">
          <HealthMark :health="data.health" />
          <RuleStrip :results="data.latest_results" />
          <button
            class="button button--quiet"
            type="button"
            :disabled="refresh.running"
            data-testid="run-dataset"
            @click="refresh.runChecks(data.dataset)"
          >
            {{ refresh.running ? 'Running…' : `Run ${data.dataset} checks` }}
          </button>
        </div>
      </header>

      <section v-if="failing.length" class="section" aria-labelledby="failing-title">
        <h2 id="failing-title" class="section-title">Failing rules</h2>
        <ul class="failures">
          <FailureItem
            v-for="f in failing"
            :key="`${f.result_id}-${refresh.version}`"
            :result="f"
          />
        </ul>
      </section>

      <section class="section" aria-labelledby="rules-title">
        <h2 id="rules-title" class="section-title">Every rule in the contract</h2>
        <div class="table-scroll">
          <table class="data-table" data-testid="rules-table">
            <thead>
              <tr>
                <th scope="col">Rule</th>
                <th scope="col">Type</th>
                <th scope="col">Severity</th>
                <th scope="col">Result</th>
                <th scope="col" class="num">Measured</th>
                <th scope="col" class="num">Allowed</th>
                <th scope="col">Checked</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="{ rule, result } in rows" :key="rule.id">
                <th scope="row">
                  {{ rule.id }}
                  <span v-if="rule.description" class="desc">{{ rule.description }}</span>
                </th>
                <td>{{ rule.type }}</td>
                <td><SeverityTag :severity="rule.severity" /></td>
                <td>
                  <span v-if="!result" class="muted">Not run yet</span>
                  <span v-else-if="result.passed" class="pass">Passing</span>
                  <span v-else class="fail">Failing</span>
                </td>
                <td class="num">{{ result?.measured_value ?? '—' }}</td>
                <td class="num">{{ result?.threshold ?? '—' }}</td>
                <td>{{ result ? timeAgo(result.checked_at) : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: var(--space-5);
  font-size: var(--step--1);
}

.head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-5);
}

.head__side {
  display: grid;
  gap: var(--space-3);
  justify-items: start;
  align-content: start;
}

.meta {
  margin-top: var(--space-3);
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.failures {
  margin: 0;
  padding: 0;
  list-style: none;
}

.desc {
  display: block;
  font-weight: 400;
  color: var(--ink-muted);
}

.data-table th[scope='row'] {
  color: var(--ink);
}

.pass {
  color: var(--pass);
  font-weight: 600;
}

.fail {
  color: var(--critical);
  font-weight: 600;
}

.muted {
  color: var(--ink-muted);
}
</style>
