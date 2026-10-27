import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// The browser calls /api/...; Vite forwards it to the rules engine.
// No CORS setup needed. Override with: ENGINE_URL=http://localhost:8001 npm run dev
const engineProxy = {
  '/api': {
    target: process.env.ENGINE_URL || 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: { proxy: engineProxy },
  preview: { proxy: engineProxy },
})
