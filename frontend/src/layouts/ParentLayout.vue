<template>
  <el-container class="family-shell">
    <el-header class="family-header">
      <router-link class="brand" to="/parent/children" aria-label="返回家长端首页">
        <img class="school-logo" :src="schoolLogo" alt="易飞特菁英" />
        <span class="brand-divider" aria-hidden="true"></span>
        <span class="brand-copy">
          <strong>一生一案</strong>
          <small>家长查阅端</small>
        </span>
      </router-link>

      <div class="account">
        <div class="identity">
          <span class="identity-name">{{ auth.user?.name || '家长' }}</span>
          <span class="identity-role">家长</span>
        </div>
        <button class="logout-button" type="button" @click="onLogout">退出登录</button>
      </div>
    </el-header>

    <el-main class="family-main"><router-view /></el-main>

    <footer class="family-footer">
      <span>易飞特菁英全日制</span>
      <span class="footer-rule" aria-hidden="true"></span>
      <span>让优秀成为习惯，为未来持续赋能</span>
    </footer>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import schoolLogo from '../assets/yifeite-logo.png'

const router = useRouter()
const auth = useAuthStore()

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.family-shell {
  --family-ink: #20221f;
  --family-muted: #676b65;
  --family-line: #d9dad6;
  --family-surface: #f5f5f3;
  --family-accent: #123f83;
  --family-orange: #f28a18;
  min-height: 100vh;
  background: var(--family-surface);
  color: var(--family-ink);
}

.family-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
  padding: 0 max(24px, calc((100vw - 1160px) / 2));
  background: rgba(255, 255, 255, 0.97);
  border-bottom: 1px solid var(--family-line);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.school-logo {
  display: block;
  width: 126px;
  height: 43px;
  object-fit: contain;
}

.brand-divider {
  width: 1px;
  height: 30px;
  background: #d7d9dc;
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  color: #173e78;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.brand-copy small {
  color: var(--family-muted);
  font-size: 11px;
  letter-spacing: 0.14em;
}

.account {
  display: flex;
  align-items: center;
  gap: 22px;
}

.identity {
  display: flex;
  align-items: baseline;
  gap: 9px;
}

.identity-name {
  font-size: 14px;
  font-weight: 650;
}

.identity-role {
  color: var(--family-muted);
  font-size: 12px;
}

.logout-button {
  padding: 0 0 2px;
  border: 0;
  border-bottom: 1px solid transparent;
  background: transparent;
  color: var(--family-muted);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: color 180ms ease, border-color 180ms ease;
}

.logout-button:hover {
  color: var(--family-ink);
  border-color: currentColor;
}

.brand:focus-visible,
.logout-button:focus-visible {
  outline: 2px solid var(--family-accent);
  outline-offset: 4px;
}

.family-main {
  position: relative;
  overflow: visible;
  padding: 0;
}

.family-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  min-height: 76px;
  padding: 20px 24px;
  color: #737770;
  font-size: 12px;
}

.footer-rule {
  width: 28px;
  height: 1px;
  background: #b8bab5;
}

@media (max-width: 640px) {
  .family-header { height: 64px; padding: 0 18px; }
  .school-logo { width: 108px; height: 38px; }
  .brand-divider, .brand-copy, .identity-role { display: none; }
  .account { gap: 14px; }
  .family-footer { flex-direction: column; gap: 7px; text-align: center; }
  .footer-rule { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .logout-button { transition: none; }
}
</style>
