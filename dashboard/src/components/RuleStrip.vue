<script setup lang="ts">
import { computed } from 'vue'

import type { Result, Severity } from '@/api'
import { SEVERITY_ORDER, severityLabel } from '@/format'

/**
 * One tile per rule. Height = severity, fill = failing.
 * Read left to right: most severe rules first.
 */
const props = defineProps<{ results: Result[] }>()

const ordered = computed(() =>
  [...props.results].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity) ||
      Number(a.passed) - Number(b.passed) ||
      a.rule_id.localeCompare(b.rule_id),
  ),
)

const heights: Record<Severity, number> = { critical: 100, high: 78, medium: 58, low: 40 }

function label(r: Result) {
  return `${r.rule_id}: ${r.passed ? 'passing' : 'failing'}, ${severityLabel[r.severity].toLowerCase()} severity`
}
</script>

<template>
  <ul class="strip" data-testid="rule-strip">
    <li
      v-for="r in ordered"
      :key="r.rule_id"
      class="tile"
      :class="[r.passed ? 'tile--pass' : `tile--fail tile--${r.severity}`]"
      :style="{ '--h': heights[r.severity] + '%' }"
      :title="label(r)"
      :data-testid="`tile-${r.rule_id}`"
    >
      <span class="visually-hidden">{{ label(r) }}</span>
    </li>
  </ul>
</template>

<style scoped>
.strip {
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 2.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.tile {
  width: 1.1rem;
  height: var(--h);
  border-radius: 2px;
}

.tile--pass {
  border: 2px solid var(--pass);
  background: transparent;
}

.tile--fail {
  background: var(--sev);
  /* A notch cut into failing tiles: shape, not just colour. */
  clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%, 0 62%, 35% 50%, 0 38%);
}

.tile--critical {
  --sev: var(--critical);
}
.tile--high {
  --sev: var(--high);
}
.tile--medium {
  --sev: var(--medium);
}
.tile--low {
  --sev: var(--low);
}
</style>
