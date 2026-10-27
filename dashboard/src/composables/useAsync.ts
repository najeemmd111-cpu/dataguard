import { ref, shallowRef, watch, type WatchSource } from 'vue'

import { ApiError } from '@/api'
import { useRefreshStore } from '@/stores/refresh'

/**
 * Load data, expose loading / error state, and reload whenever
 * checks are run anywhere in the app (refresh store) or a source changes.
 */
export function useAsync<T>(loader: () => Promise<T>, sources: WatchSource[] = []) {
  const data = shallowRef<T | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(true)
  const refresh = useRefreshStore()

  async function load() {
    loading.value = true
    error.value = null
    try {
      data.value = await loader()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Something went wrong while loading.'
    } finally {
      loading.value = false
    }
  }

  watch([() => refresh.version, ...sources], load, { immediate: true })

  return { data, error, loading, reload: load }
}
