import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const envFrontend = loadEnv(mode, process.cwd(), '')
  const envRoot = loadEnv(mode, path.resolve(process.cwd(), '..'), '')
  // 允许本地调试临时切换后端端口，避免陈旧进程占用默认端口时代理仍指向旧代码。
  const backendPort = process.env.BACKEND_PORT || envFrontend.BACKEND_PORT || envRoot.BACKEND_PORT || 8000

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
