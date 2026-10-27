<script setup lang="ts">
import type { Health } from '@/api'
import { healthLabel } from '@/format'

defineProps<{ health: Health }>()
</script>

<template>
  <span class="health" :class="`health--${health}`" :data-testid="`health-${health}`">
    <svg class="health__icon" viewBox="0 0 16 16" aria-hidden="true">
      <!-- Shape differs per state, so colour is never the only signal. -->
      <path v-if="health === 'green'" d="M3 8.5l3.2 3L13 4.5" />
      <path v-else-if="health === 'amber'" d="M8 2.5l6 11H2z M8 6.5v3.5 M8 11.8v.2" />
      <path v-else-if="health === 'red'" d="M4 4l8 8 M12 4l-8 8" />
      <circle v-else cx="8" cy="8" r="5" />
    </svg>
    {{ healthLabel[health] }}
  </span>
</template>

<style scoped>
.health {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  font-weight: 600;
  font-variation-settings: 'wdth' 92;
  white-space: nowrap;
}

.health__icon {
  width: 1em;
  height: 1em;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.health--green {
  color: var(--pass);
}
.health--amber {
  color: var(--medium);
}
.health--red {
  color: var(--critical);
}
.health--unknown {
  color: var(--ink-muted);
}
</style>
