<template>
  <el-container class="family-shell">
    <el-header class="family-header">
      <div class="brand">
        <span class="brand-mark">家</span>
        <div class="brand-info">
          <strong>一生一案</strong>
          <small>家长协同端</small>
        </div>
      </div>
      <div class="account">
        <div class="user-chip">
          <span class="avatar-dot"></span>
          <span>{{ auth.user?.name || '家长' }}</span>
        </div>
        <div class="divider"></div>
        <el-button link class="logout-btn" @click="onLogout">退出登录</el-button>
      </div>
    </el-header>
    <el-main class="family-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.family-shell {
  min-height: 100vh;
  background: var(--app-bg);
}

.family-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 max(20px, calc((100vw - 1240px) / 2));
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: #ffffff;
  background: #1a2233;
  border-radius: 7px;
  font-weight: 700;
  font-size: 14px;
}

.brand-info {
  display: grid;
  gap: 1px;
}

.brand-info strong {
  font-size: 13.5px;
  color: var(--ink);
  font-weight: 600;
}

.brand-info small {
  color: var(--ink-muted);
  font-size: 11px;
}

.account {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #334155;
  font-weight: 500;
}

.avatar-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.divider {
  width: 1px;
  height: 16px;
  background: var(--line);
}

.logout-btn {
  color: #6b778d;
  font-size: 13px;
}

.family-main {
  width: 100%;
  padding: 0;
  overflow: visible;
}
</style>
