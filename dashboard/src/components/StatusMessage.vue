<script setup lang="ts">
defineProps<{ kind: 'loading' | 'error' | 'empty'; message?: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="status" :class="`status--${kind}`" :data-testid="`status-${kind}`" role="status">
    <template v-if="kind === 'loading'">Loading…</template>
    <template v-else-if="kind === 'error'">
      <p>
        <strong>{{ message }}</strong>
      </p>
      <p class="status__hint">
        Start it from the project folder with <code>docker compose up -d</code>, then try again.
      </p>
      <button class="button button--quiet" type="button" @click="$emit('retry')">Try again</button>
    </template>
    <template v-else>
      <slot>{{ message }}</slot>
    </template>
  </div>
</template>

<style scoped>
.status {
  padding: var(--space-5) 0;
  color: var(--ink-muted);
}

.status--error {
  display: grid;
  gap: var(--space-3);
  justify-items: start;
  color: var(--ink);
  border-left: 4px solid var(--critical);
  padding-left: var(--space-4);
}

.status__hint {
  color: var(--ink-muted);
}

code {
  font-size: 0.95em;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 0 0.3em;
}
</style>
