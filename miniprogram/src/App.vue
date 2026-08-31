<script setup>
import { onLaunch, onShow } from '@dcloudio/uni-app'
import { useAuthStore } from './stores/auth'

onLaunch(() => {
  const auth = useAuthStore()
  auth.restore()
})

onShow(() => {
  // 小程序切前台时可校验会话
})
</script>

<style>
page {
  background: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>
