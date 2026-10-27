<script setup lang="ts">
import { computed, ref } from 'vue'

import { api } from '@/api'
import StatusMessage from '@/components/StatusMessage.vue'
import { useAsync } from '@/composables/useAsync'
import { dateTime } from '@/format'

const { data, error, loading, reload } = useAsync(() => api.audit(500))

type Filter = 'all' | 'allowed' | 'denied'
const filter = ref<Filter>('all')

const rows = computed(() =>
  (data.value ?? []).filter((e) =>
    filter.value === 'all' ? true : filter.value === 'allowed' ? e.allowed : !e.allowed,
  ),
)

const counts = computed(() => ({
  all: data.value?.length ?? 0,
  allowed: data.value?.filter((e) => e.allowed).length ?? 0,
  denied: data.value?.filter((e) => !e.allowed).length ?? 0,
}))

const outcomeLabel = { ok: 'Done', denied: 'Refused', error: 'Failed' } as const
</script>

<template>
  <div class="page">
    <h1 class="page-title">AI access log</h1>
    <p class="lede">
      Every tool call made through the MCP server: who asked, with which role, and whether it was
      allowed. Refused calls are recorded too.
    </p>

    <StatusMessage v-if="loading && !data" kind="loading" />
    <StatusMessage v-else-if="error" kind="error" :message="error" @retry="reload" />
    <StatusMessage v-else-if="!data?.length" kind="empty">
      No AI calls yet. Connect an MCP client, such as the MCP Inspector or Claude Desktop, and its
      calls will appear here.
    </StatusMessage>

    <template v-else>
      <fieldset class="filter">
        <legend class="visually-hidden">Show calls</legend>
        <label v-for="f in ['all', 'allowed', 'denied'] as const" :key="f">
          <input
            v-model="filter"
            type="radio"
            name="audit-filter"
            :value="f"
            :data-testid="`filter-${f}`"
          />
          {{ { all: 'All', allowed: 'Allowed', denied: 'Refused' }[f] }} ({{ counts[f] }})
        </label>
      </fieldset>

      <div class="table-scroll" tabindex="0" role="region" aria-label="AI tool calls">
        <table class="data-table" data-testid="audit-table">
          <thead>
            <tr>
              <th scope="col">When</th>
              <th scope="col">Client</th>
              <th scope="col">Role</th>
              <th scope="col">Tool</th>
              <th scope="col">Arguments</th>
              <th scope="col">Outcome</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in rows" :key="e.audit_id" :class="{ refused: !e.allowed }">
              <td>{{ dateTime(e.at) }}</td>
              <td>{{ e.client }}</td>
              <td>{{ e.role }}</td>
              <td>
                <strong>{{ e.tool }}</strong>
              </td>
              <td class="args">{{ JSON.stringify(e.arguments) }}</td>
              <td :class="`outcome outcome--${e.outcome}`">
                {{ outcomeLabel[e.outcome] }}
                <span v-if="e.detail" class="detail">{{ e.detail }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.filter {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  margin: var(--space-5) 0 var(--space-3);
  padding: 0;
  border: 0;
}

.filter label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.args {
  max-width: 28rem;
  overflow-wrap: anywhere;
  color: var(--ink-muted);
}

.refused td:first-child {
  box-shadow: inset 3px 0 0 var(--critical);
}

.outcome {
  font-weight: 600;
}
.outcome--ok {
  color: var(--pass);
}
.outcome--denied,
.outcome--error {
  color: var(--critical);
}

.detail {
  display: block;
  font-weight: 400;
  color: var(--ink-muted);
}
</style>
