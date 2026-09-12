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
@import "./styles/theme.css";
</style>
