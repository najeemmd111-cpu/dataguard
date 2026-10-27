<script setup lang="ts">
import { computed } from 'vue'

import { api } from '@/api'
import StatusMessage from '@/components/StatusMessage.vue'
import { useAsync } from '@/composables/useAsync'
import { dateTime } from '@/format'

const { data, error, loading, reload } = useAsync(() => api.runs(40))

/** Oldest to newest for the chart. */
const chronological = computed(() => [...(data.value ?? [])].reverse())
const maxRules = computed(() => Math.max(1, ...chronological.value.map((r) => r.total_rules)))

const BAR = 14
const GAP = 6
const HEIGHT = 120
</script>

<template>
  <div class="page">
    <h1 class="page-title">Run history</h1>
    <p class="lede">
      Every check run, whether you started it here, through the API, or the schedule did.
    </p>

    <StatusMessage v-if="loading && !data" kind="loading" />
    <StatusMessage v-else-if="error" kind="error" :message="error" @retry="reload" />
    <StatusMessage v-else-if="!data?.length" kind="empty">
      No runs yet. Use Run all checks at the top of the page to start the first one.
    </StatusMessage>

    <template v-else>
      <figure class="chart" data-testid="runs-chart">
        <svg
          :viewBox="`0 0 ${chronological.length * (BAR + GAP)} ${HEIGHT}`"
          preserveAspectRatio="none"
          :style="{ maxWidth: `${chronological.length * 28}px` }"
          role="img"
          :aria-label="`Failed rules per run for the last ${chronological.length} runs`"
        >
          <g v-for="(r, i) in chronological" :key="r.run_id">
            <rect
              class="chart__total"
              :x="i * (BAR + GAP)"
              :y="HEIGHT - (r.total_rules / maxRules) * HEIGHT"
              :width="BAR"
              :height="(r.total_rules / maxRules) * HEIGHT"
            />
            <rect
              class="chart__failed"
              :x="i * (BAR + GAP)"
              :y="HEIGHT - (r.failed_rules / maxRules) * HEIGHT"
              :width="BAR"
              :height="(r.failed_rules / maxRules) * HEIGHT"
            >
              <title>Run {{ r.run_id }}: {{ r.failed_rules }} of {{ r.total_rules }} failed</title>
            </rect>
          </g>
        </svg>
        <figcaption>
          Outlined bars are rules checked in each run; the filled part is how many failed. Oldest on
          the left.
        </figcaption>
      </figure>

      <div class="table-scroll section" tabindex="0" role="region" aria-label="Check runs">
        <table class="data-table" data-testid="runs-table">
          <thead>
            <tr>
              <th scope="col" class="num">Run</th>
              <th scope="col">Started</th>
              <th scope="col">Started by</th>
              <th scope="col">Scope</th>
              <th scope="col">Outcome</th>
              <th scope="col" class="num">Failed</th>
              <th scope="col" class="num">Checked</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in data" :key="r.run_id">
              <td class="num">{{ r.run_id }}</td>
              <td>{{ dateTime(r.started_at) }}</td>
              <td>
                {{
                  r.trigger === 'schedule'
                    ? 'Schedule'
                    : r.trigger === 'api'
                      ? 'API or dashboard'
                      : 'Manual'
                }}
              </td>
              <td>{{ r.dataset ?? 'All contracts' }}</td>
              <td :class="`outcome outcome--${r.status}`">
                {{
                  {
                    passed: 'All passed',
                    failed: 'Some failed',
                    error: 'Run error',
                    running: 'Running',
                  }[r.status]
                }}
              </td>
              <td class="num">{{ r.failed_rules }}</td>
              <td class="num">{{ r.total_rules }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.chart {
  margin: var(--space-6) 0 0;
}

.chart svg {
  display: block;
  width: 100%;
  height: 160px;
  border-bottom: 2px solid var(--ink);
}

.chart__total {
  fill: none;
  stroke: var(--line-strong);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}

.chart__failed {
  fill: var(--critical);
}

figcaption {
  margin-top: var(--space-2);
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.outcome {
  font-weight: 600;
}
.outcome--passed {
  color: var(--pass);
}
.outcome--failed,
.outcome--error {
  color: var(--critical);
}
</style>
