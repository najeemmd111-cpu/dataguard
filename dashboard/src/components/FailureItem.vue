<script setup lang="ts">
import { ref } from 'vue'

import { api, ApiError, type Annotation, type Result } from '@/api'
import { dateTime, timeAgo } from '@/format'

import SampleTable from './SampleTable.vue'
import SeverityTag from './SeverityTag.vue'

const props = defineProps<{ result: Result; showDataset?: boolean }>()

const open = ref(false)
const notes = ref<Annotation[]>([...props.result.annotations])
const draft = ref('')
const saving = ref(false)
const saveError = ref<string | null>(null)
const detailsId = `failure-${props.result.result_id}`

async function addNote() {
  const note = draft.value.trim()
  if (!note) return
  saving.value = true
  saveError.value = null
  try {
    notes.value.push(await api.annotate(props.result.result_id, note))
    draft.value = ''
  } catch (err) {
    saveError.value = err instanceof ApiError ? err.message : 'The note could not be saved.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <li class="failure" :data-testid="`failure-${result.rule_id}`">
    <button
      class="failure__head"
      type="button"
      :aria-expanded="open"
      :aria-controls="detailsId"
      @click="open = !open"
    >
      <SeverityTag :severity="result.severity" />
      <span class="failure__name">
        <span v-if="showDataset" class="failure__dataset">{{ result.dataset }} / </span
        >{{ result.rule_id }}
      </span>
      <span class="failure__message">{{ result.message }}</span>
      <span class="failure__chevron" aria-hidden="true">{{ open ? '−' : '+' }}</span>
    </button>

    <div v-if="open" :id="detailsId" class="failure__body">
      <dl class="facts">
        <div>
          <dt>Measured</dt>
          <dd>{{ result.measured_value }}</dd>
        </div>
        <div>
          <dt>Allowed</dt>
          <dd>{{ result.threshold }}</dd>
        </div>
        <div>
          <dt>Rule type</dt>
          <dd>{{ result.rule_type }}</dd>
        </div>
        <div>
          <dt>Checked</dt>
          <dd :title="dateTime(result.checked_at)">{{ timeAgo(result.checked_at) }}</dd>
        </div>
      </dl>

      <template v-if="result.sample_rows.length">
        <h4 class="sub">Sample rows</h4>
        <SampleTable :rows="result.sample_rows" :caption="`Sample rows for ${result.rule_id}`" />
      </template>

      <h4 class="sub">Notes</h4>
      <ul v-if="notes.length" class="notes" data-testid="notes">
        <li v-for="n in notes" :key="n.annotation_id">
          <p>{{ n.note }}</p>
          <p class="notes__meta">{{ n.author }}, {{ dateTime(n.created_at) }}</p>
        </li>
      </ul>
      <p v-else class="notes__empty">No notes yet. Add what you know about the cause.</p>

      <form class="note-form" @submit.prevent="addNote">
        <label :for="`${detailsId}-note`">Add a note</label>
        <div class="note-form__row">
          <input
            :id="`${detailsId}-note`"
            v-model="draft"
            type="text"
            maxlength="2000"
            placeholder="For example: sales ETL paused since Monday"
            data-testid="note-input"
          />
          <button class="button" type="submit" :disabled="saving || !draft.trim()">
            {{ saving ? 'Saving…' : 'Save note' }}
          </button>
        </div>
        <p v-if="saveError" class="note-form__error" role="alert">{{ saveError }}</p>
      </form>
    </div>
  </li>
</template>

<style scoped>
.failure {
  border-bottom: 1px solid var(--line);
}

.failure__head {
  display: grid;
  grid-template-columns: 6.5rem minmax(12rem, 21rem) 1fr auto;
  gap: var(--space-4);
  align-items: baseline;
  width: 100%;
  padding: var(--space-4) var(--space-2);
  border: 0;
  background: none;
  text-align: left;
  cursor: pointer;
}

.failure__head:hover {
  background: var(--surface);
}

.failure__name {
  font-weight: 600;
  overflow-wrap: anywhere;
}

.failure__dataset {
  color: var(--ink-muted);
  font-weight: 400;
}

.failure__message {
  color: var(--ink-muted);
  font-variation-settings: 'wdth' 90;
}

.failure__chevron {
  font-size: var(--step-1);
  color: var(--ink-muted);
  width: 1rem;
  text-align: center;
}

.failure__body {
  padding: 0 var(--space-2) var(--space-5) calc(6.5rem + var(--space-4) + var(--space-2));
}

.facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-6);
  margin: 0 0 var(--space-4);
}

.facts dt {
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.facts dd {
  margin: 0;
  font-size: var(--step-1);
  font-weight: 600;
}

.sub {
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--step-0);
}

.notes {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: var(--space-3);
}

.notes li {
  border-left: 3px solid var(--line-strong);
  padding-left: var(--space-3);
}

.notes__meta,
.notes__empty {
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.note-form {
  margin-top: var(--space-4);
  max-width: 44rem;
}

.note-form label {
  display: block;
  font-weight: 600;
  margin-bottom: var(--space-1);
}

.note-form__row {
  display: flex;
  gap: var(--space-2);
}

.note-form input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--ink);
  font: inherit;
}

.note-form__error {
  margin-top: var(--space-2);
  color: var(--critical);
}

@media (max-width: 760px) {
  .failure__head {
    grid-template-columns: 1fr auto;
  }
  .failure__name {
    grid-column: 1;
  }
  .failure__message {
    grid-column: 1 / -1;
  }
  .failure__chevron {
    grid-row: 1;
    grid-column: 2;
  }
  .failure__body {
    padding-left: var(--space-2);
  }
  .note-form__row {
    flex-direction: column;
  }
}
</style>
