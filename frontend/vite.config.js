import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const envFrontend = loadEnv(mode, process.cwd(), '')
  const envRoot = loadEnv(mode, path.resolve(process.cwd(), '..'), '')
  const backendPort = envFrontend.BACKEND_PORT || envRoot.BACKEND_PORT || 8000

  return {
    plugins: [vue()],
    server: {
      port: 5174,
      strictPort: true,
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
