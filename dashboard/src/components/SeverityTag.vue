<script setup lang="ts">
import type { Severity } from '@/api'
import { severityLabel } from '@/format'

defineProps<{ severity: Severity }>()
</script>

<template>
  <span class="sev" :class="`sev--${severity}`">
    <span class="sev__bar" aria-hidden="true"></span>{{ severityLabel[severity] }}
  </span>
</template>

<style scoped>
.sev {
  display: inline-block;
  font-weight: 600;
  font-variation-settings: 'wdth' 88;
  white-space: nowrap;
}

/* Same height scale as the rule strip. */
.sev__bar {
  display: inline-block;
  vertical-align: -0.1em;
  margin-right: 0.4em;
  width: 0.4em;
  background: var(--sev);
  border-radius: 1px;
}
.sev--critical {
  --sev: var(--critical);
}
.sev--critical .sev__bar {
  height: 1em;
}
.sev--high {
  --sev: var(--high);
}
.sev--high .sev__bar {
  height: 0.8em;
}
.sev--medium {
  --sev: var(--medium);
}
.sev--medium .sev__bar {
  height: 0.6em;
}
.sev--low {
  --sev: var(--low);
}
.sev--low .sev__bar {
  height: 0.42em;
}
</style>
