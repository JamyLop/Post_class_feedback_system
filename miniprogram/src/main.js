import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { useAuthStore } from './stores/auth'

export function createApp() {
  const app = createSSRApp(App)
  const pinia = createPinia()
  app.use(pinia)
  // 页面守卫和首屏渲染前恢复会话，直接进入业务页时也能识别已登录角色。
  useAuthStore(pinia).restore()
  return {
    app,
    pinia,
  }
}
