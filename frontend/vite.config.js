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
      host: '127.0.0.1',
      port: 5174,
      strictPort: true,
      proxy: {
        '/api': {
          // Keep the dev proxy on IPv4; uvicorn commonly binds 127.0.0.1 only.
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
