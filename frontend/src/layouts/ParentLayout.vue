<template>
  <el-container class="family-shell">
    <el-header class="family-header">
      <div class="brand"><span class="brand-mark">家</span><div><strong>一生一案</strong><small>家长阅读端</small></div></div>
      <div class="account"><span>{{ auth.user?.name }}</span><el-button link @click="onLogout">退出登录</el-button></div>
    </el-header>
    <el-main class="family-main"><router-view /></el-main>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
function onLogout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.family-shell { min-height: 100vh; background: var(--app-bg); }.family-header { display: flex; align-items: center; justify-content: space-between; height: 68px; padding: 0 max(24px, calc((100vw - 1180px) / 2)); background: var(--surface); border-bottom: 1px solid var(--line); }.brand, .account { display: flex; align-items: center; gap: 12px; }.brand-mark { display: grid; place-items: center; width: 34px; height: 34px; color: #fff; background: var(--brand); border-radius: 9px; font-weight: 800; }.brand > div { display: grid; gap: 1px; }.brand strong { font-size: 15px; }.brand small, .account { color: var(--ink-muted); font-size: 12px; }.family-main { width: 100%; padding: 0; overflow: visible; }
</style>
