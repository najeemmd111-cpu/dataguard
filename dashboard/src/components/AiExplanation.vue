<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type Investigation } from '@/api'
import { dateTime } from '@/format'
import { seconds } from '@/usage'

const props = defineProps<{ dataset: string; ruleId: string }>()

const state = ref<'loading' | 'none' | 'ready' | 'unavailable'>('loading')
const latest = ref<Investigation | null>(null)

onMounted(async () => {
  try {
    const [found] = await api.investigations({
      dataset: props.dataset,
      rule_id: props.ruleId,
      status: 'ok',
      limit: 1,
    })
    latest.value = found ?? null
    state.value = found ? 'ready' : 'none'
  } catch {
    state.value = 'unavailable'
  }
})
</script>

<template>
  <section class="ai" :aria-labelledby="`ai-${dataset}-${ruleId}`" :data-testid="`ai-${ruleId}`">
    <h4 :id="`ai-${dataset}-${ruleId}`" class="ai__title">AI explanation</h4>

    <p v-if="state === 'loading'" class="ai__muted">Looking for an explanation…</p>
    <p v-else-if="state === 'unavailable'" class="ai__muted">Explanations could not be loaded.</p>
    <p v-else-if="state === 'none'" class="ai__muted" data-testid="ai-none">
      No explanation yet. Ask the agent from the project folder:
      <code>docker compose run --rm agent investigate {{ ruleId }}</code>
    </p>

    <template v-else-if="latest?.answer">
      <p class="ai__summary">{{ latest.answer.summary }}</p>
      <dl class="ai__body">
        <dt>Likely cause</dt>
        <dd>{{ latest.answer.likely_cause }}</dd>
        <dt>Evidence</dt>
        <dd>
          <ul>
            <li v-for="(e, i) in latest.answer.evidence" :key="i">{{ e }}</li>
          </ul>
        </dd>
        <dt>Fix</dt>
        <dd>
          <ol>
            <li v-for="(f, i) in latest.answer.fix_steps" :key="i">{{ f }}</li>
          </ol>
        </dd>
        <template v-if="latest.answer.sources.length">
          <dt>Based on</dt>
          <dd class="ai__sources">
            <code v-for="s in latest.answer.sources" :key="s">{{ s }}</code>
          </dd>
        </template>
      </dl>
      <p class="ai__meta">
        Confidence: {{ latest.answer.confidence }}. {{ latest.model }}, {{ latest.tool_calls }} tool
        {{ latest.tool_calls === 1 ? 'call' : 'calls' }}, {{ seconds(latest.latency_ms) }},
        {{ dateTime(latest.created_at) }}. Written by a language model: check the evidence before
        acting.
      </p>
    </template>
  </section>
</template>

<style scoped>
.ai {
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid var(--action);
  background: var(--surface);
  max-width: 52rem;
}

.ai__title {
  margin: 0 0 var(--space-2);
  font-size: var(--step-0);
}

.ai__summary {
  font-weight: 600;
}

.ai__body {
  margin: var(--space-3) 0 0;
}

.ai__body dt {
  margin-top: var(--space-2);
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.ai__body dd {
  margin: 0;
}

.ai__body ul,
.ai__body ol {
  margin: 0;
  padding-left: 1.2rem;
}

.ai__sources {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.ai__muted,
.ai__meta {
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.ai__meta {
  margin-top: var(--space-3);
}

code {
  font-size: 0.92em;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 0 0.3em;
  overflow-wrap: anywhere;
}
</style>
