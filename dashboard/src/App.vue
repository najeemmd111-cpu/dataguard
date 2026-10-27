<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

import { useRefreshStore } from '@/stores/refresh'
import { plural } from '@/format'

const refresh = useRefreshStore()
</script>

<template>
  <a class="skip" href="#main">Skip to content</a>
  <header class="bar">
    <div class="bar__inner">
      <RouterLink class="mark" :to="{ name: 'overview' }" aria-label="DataGuard home">
        <svg viewBox="0 0 20 22" aria-hidden="true">
          <!-- A contract seal: a shield with a check. -->
          <path d="M10 1.5 18 4.5v6.2c0 4.6-3.3 8.4-8 9.8-4.7-1.4-8-5.2-8-9.8V4.5z" />
          <path class="mark__tick" d="m6.3 11 2.6 2.5 4.9-5.3" />
        </svg>
        DataGuard
      </RouterLink>

      <nav aria-label="Main">
        <RouterLink :to="{ name: 'overview' }">Overview</RouterLink>
        <RouterLink :to="{ name: 'runs' }">Run history</RouterLink>
        <RouterLink :to="{ name: 'audit' }">AI access log</RouterLink>
      </nav>

      <button
        class="button"
        type="button"
        :disabled="refresh.running"
        data-testid="run-all"
        @click="refresh.runChecks()"
      >
        {{ refresh.running ? 'Running checks…' : 'Run all checks' }}
      </button>
    </div>

    <p v-if="refresh.runError" class="bar__note bar__note--error" role="alert">
      Checks could not run: {{ refresh.runError }}
    </p>
    <p v-else-if="refresh.lastRun" class="bar__note" role="status" data-testid="run-result">
      Run {{ refresh.lastRun.run_id }} finished: {{ refresh.lastRun.failed_rules }} of
      {{ plural(refresh.lastRun.total_rules, 'check') }} failing.
    </p>
  </header>

  <main id="main">
    <RouterView />
  </main>
</template>

<style scoped>
.skip {
  position: absolute;
  left: var(--space-4);
  top: -3rem;
  padding: var(--space-2) var(--space-3);
  background: var(--surface);
  z-index: 10;
}

.skip:focus {
  top: var(--space-2);
}

.bar {
  border-bottom: 1px solid var(--line);
  background: var(--paper);
}

.bar__inner {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  max-width: var(--page);
  margin: 0 auto;
  padding: var(--space-3) var(--space-5);
}

.mark {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 800;
  font-size: var(--step-1);
  font-variation-settings: 'wdth' 112;
  color: var(--ink);
  text-decoration: none;
}

.mark svg {
  width: 1.25rem;
  height: 1.4rem;
  fill: var(--ink);
}

.mark__tick {
  fill: none;
  stroke: var(--paper);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

nav {
  display: flex;
  gap: var(--space-5);
  flex: 1;
}

nav a {
  padding: var(--space-2) 0;
  color: var(--ink-muted);
  text-decoration: none;
  font-weight: 500;
  border-bottom: 2px solid transparent;
}

nav a:hover {
  color: var(--ink);
}

nav a.router-link-exact-active {
  color: var(--ink);
  border-bottom-color: var(--ink);
}

.bar__note {
  max-width: var(--page);
  margin: 0 auto;
  padding: 0 var(--space-5) var(--space-3);
  font-size: var(--step--1);
  color: var(--ink-muted);
}

.bar__note--error {
  color: var(--critical);
}

@media (max-width: 760px) {
  .bar__inner {
    flex-wrap: wrap;
    gap: var(--space-3) var(--space-5);
    padding: var(--space-3) var(--space-4);
  }
  nav {
    order: 3;
    flex-basis: 100%;
    overflow-x: auto;
  }
  .bar__inner > .button {
    margin-left: auto;
  }
}
</style>
