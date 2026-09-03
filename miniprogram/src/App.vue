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
  background: #F4F6F5;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  color: #203235;
  line-height: 1.55;
}
view, text { box-sizing: border-box; }
::-webkit-scrollbar { display: none; }
</style>
