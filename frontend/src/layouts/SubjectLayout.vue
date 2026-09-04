<template>
  <el-container class="app-shell">
    <el-aside width="228px" class="aside">
      <div class="brand">
        <div class="brand-mark">任</div>
        <div class="brand-copy">
          <strong>一生一案</strong>
          <span>任课教学协同</span>
        </div>
      </div>

      <el-scrollbar class="nav-scroll">
        <div class="nav-label">所带学科</div>
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/subject/cases">
            <el-icon><Files /></el-icon>
            <span>班级档案与科目方案</span>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>

      <div class="subject-note">
        <span class="subject-dot"></span>
        <div class="subject-text">
          <strong>只读协同</strong>
          <small>查看所带学科方案，意见走学科建议</small>
        </div>
      </div>
    </el-aside>

    <el-container class="main-container">
      <el-header class="header">
        <div class="header-left">
          <span class="role-title">任课老师工作台</span>
          <span class="context-tag">所带学科 · 方案查阅与建议</span>
        </div>
        <div class="header-right">
          <div class="user-profile">
            <span class="avatar-badge">任</span>
            <div class="user-meta">
              <strong class="user-name">{{ auth.user?.name || '任课老师' }}</strong>
              <small class="user-role-text">任课老师</small>
            </div>
          </div>
          <div class="divider"></div>
          <el-button link class="logout-btn" @click="onLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="workspace">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { Files } from '@element-plus/icons-vue'
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
.app-shell { height: 100vh; min-width: 0; overflow: hidden; background: var(--app-bg); }
.aside {
  display: flex;
  flex-direction: column;
  width: 228px !important;
  background: var(--side-bg);
  border-right: 1px solid var(--side-line);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--side-line);
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 7px;
  color: #fff;
  background: #0d9488;
  font-weight: 700;
  font-size: 14px;
}
.brand-copy { display: grid; gap: 1px; }
.brand-copy strong { color: #e8ecf3; font-size: 13.5px; font-weight: 600; }
.brand-copy span { color: #6b778d; font-size: 11px; }
.nav-scroll { flex: 1; padding: 14px 0 8px; }
.nav-label { padding: 6px 18px 8px; color: #5a6782; font-size: 11px; }
:deep(.el-menu) { border-right: 0; background: transparent; }
:deep(.el-menu-item) {
  height: 38px;
  margin: 1px 8px;
  padding: 0 12px !important;
  border-radius: 8px;
  color: #8a97ad;
  font-size: 13.5px;
}
:deep(.el-menu-item:hover) { color: #d6deeb; background: rgba(255,255,255,0.05); }
:deep(.el-menu-item.is-active) { color: #fff; background: rgba(255,255,255,0.08); font-weight: 600; }
:deep(.el-menu-item .el-icon) { font-size: 15px; margin-right: 9px; }
.subject-note {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin: 0 10px 12px;
  padding: 10px 12px;
  border: 1px solid #2a3550;
  border-radius: 10px;
  background: #1a2233;
}
.subject-dot { width: 8px; height: 8px; margin-top: 4px; border-radius: 999px; background: #14b8a6; flex-shrink: 0; }
.subject-text { display: grid; gap: 2px; }
.subject-text strong { color: #e8ecf3; font-size: 12.5px; }
.subject-text small { color: #8a97ad; font-size: 11px; line-height: 1.5; }
.main-container { min-width: 0; display: flex; flex-direction: column; }
.header {
  position: sticky; top: 0; z-index: 10;
  display: flex; justify-content: space-between; align-items: center;
  height: 56px; padding: 0 20px 0 22px;
  background: #fff; border-bottom: 1px solid var(--line);
}
.header-left { display: flex; align-items: center; gap: 10px; }
.role-title { font-weight: 650; font-size: 14px; color: var(--ink); }
.context-tag { font-size: 11.5px; color: #5b667a; background: #f2f3f5; border: 1px solid #e6e8eb; padding: 2px 7px; border-radius: 6px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-profile { display: flex; align-items: center; gap: 9px; }
.avatar-badge {
  width: 30px; height: 30px; border-radius: 999px;
  background: #ccfbf1; color: #0f766e; border: 1px solid #99f6e4;
  display: grid; place-items: center; font-weight: 600; font-size: 12.5px;
}
.user-meta { display: flex; flex-direction: column; }
.user-name { font-size: 12.5px; color: var(--ink); font-weight: 600; line-height: 1.2; }
.user-role-text { font-size: 11px; color: var(--ink-muted); }
.divider { width: 1px; height: 16px; background: var(--line); }
.logout-btn { color: #6b778d; font-size: 13px; }
.workspace { flex: 1; min-width: 0; padding: 20px 22px; overflow-x: hidden; overflow-y: auto; background: var(--app-bg); }
@media (max-width: 900px) {
  .aside { width: 60px !important; }
  .brand-copy, .nav-label, .subject-note, .user-meta { display: none; }
  .brand { justify-content: center; padding: 0; }
  :deep(.el-menu-item) { justify-content: center; padding: 0 !important; margin: 1px 6px; }
  :deep(.el-menu-item span) { display: none; }
  :deep(.el-menu-item .el-icon) { margin-right: 0; }
}
</style>
