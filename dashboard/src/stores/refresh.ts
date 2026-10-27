import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, ApiError, type Run } from '@/api'

/** Running checks from anywhere bumps `version`, and every page reloads its data. */
export const useRefreshStore = defineStore('refresh', () => {
  const version = ref(0)
  const running = ref(false)
  const lastRun = ref<Run | null>(null)
  const runError = ref<string | null>(null)

  async function runChecks(dataset?: string) {
    running.value = true
    runError.value = null
    try {
      lastRun.value = await api.runChecks(dataset)
      version.value++
    } catch (err) {
      runError.value = err instanceof ApiError ? err.message : 'Checks could not run.'
    } finally {
      running.value = false
    }
  }

  return { version, running, lastRun, runError, runChecks }
})
