<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ rows: Record<string, unknown>[]; caption: string }>()

const columns = computed(() => {
  const seen = new Set<string>()
  for (const row of props.rows) Object.keys(row).forEach((k) => seen.add(k))
  return [...seen]
})

function cell(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<template>
  <div class="table-scroll" tabindex="0" role="region" :aria-label="caption">
    <table class="data-table" data-testid="sample-table">
      <caption class="visually-hidden">
        {{
          caption
        }}
      </caption>
      <thead>
        <tr>
          <th v-for="c in columns" :key="c" scope="col">{{ c }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i">
          <td v-for="c in columns" :key="c" :class="{ missing: row[c] === null }">
            {{ cell(row[c]) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.missing {
  color: var(--critical);
  font-weight: 600;
}
</style>
