<template>
  <el-container class="app-shell">
    <el-aside width="232px" class="aside">
      <div class="brand">
        <div class="brand-mark">案</div>
        <div class="brand-copy"><strong>一生一案</strong><span>学业发展管理系统</span></div>
      </div>
      <el-scrollbar class="nav-scroll">
        <div class="nav-label">核心工作</div>
        <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/teacher/student-cases"><el-icon><Files /></el-icon><span>学生档案</span></el-menu-item>
        <el-sub-menu index="data-collection">
          <template #title><el-icon><Collection /></el-icon><span>数据采集</span></template>
          <el-menu-item index="/teacher/assignments">作业管理</el-menu-item>
          <el-menu-item index="/teacher/questions">题库</el-menu-item>
          <el-menu-item index="/teacher/reviews">教师复核</el-menu-item>
          <el-menu-item index="/teacher/student-analytics">学生学情</el-menu-item>
          <el-menu-item index="/teacher/class-analytics">班级学情</el-menu-item>
          <el-menu-item index="/teacher/feedback">课后反馈</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/teacher/classes"><el-icon><School /></el-icon><span>班级与教师</span></el-menu-item>
      </el-menu>
      </el-scrollbar>
      <div class="pilot-note"><span class="pilot-dot"></span><span>高三试点 · 2026-2027</span></div>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-context"><span>教师工作台</span><small>{{ pageContext }}</small></div>
        <div class="header-actions">
          <div class="user-chip"><span class="avatar">{{ auth.user?.name?.slice(0, 1) }}</span><span>{{ auth.user?.name }}</span></div>
          <el-button link @click="onLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main ref="workspaceRef" class="workspace"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Collection, Files, School } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const workspaceRef = ref(null)

const activeMenu = computed(() => {
  return route.path
})

const pageContext = computed(() => {
  if (route.path.includes('/student-cases/')) return '学生档案详情'
  if (route.path === '/teacher/student-cases') return '学生档案'
  return '教学数据'
})

watch(
  () => route.fullPath,
  async () => {
    await nextTick()
    // 主内容区独立滚动，路由切换后回到顶部，避免沿用列表页的滚动位置。
    const workspace = workspaceRef.value?.$el || workspaceRef.value
    workspace?.scrollTo({ top: 0, left: 0 })
  },
)

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-shell { height: 100vh; min-width: 0; overflow: hidden; }
.aside {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 232px !important;
  background: var(--sidebar);
  border-right: 1px solid rgb(255 255 255 / 7%);
}
.brand { display: flex; align-items: center; gap: 11px; height: 72px; padding: 0 20px; color: #fff; }
.brand-mark { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 9px; color: var(--sidebar); background: #fff; font-weight: 800; }
.brand-copy { display: grid; gap: 2px; min-width: 0; }
.brand-copy strong { font-size: 15px; letter-spacing: .01em; }
.brand-copy span { color: var(--sidebar-muted); font-size: 11px; white-space: nowrap; }
.nav-scroll { flex: 1; }
.nav-label { padding: 18px 24px 8px; color: color-mix(in oklch, var(--sidebar-muted) 72%, transparent); font-size: 11px; }
:deep(.el-menu) { border-right: 0; background: transparent; }
:deep(.el-menu-item), :deep(.el-sub-menu__title) { height: 44px; margin: 3px 12px; border-radius: 8px; color: var(--sidebar-muted); }
:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) { color: #fff; background: rgb(255 255 255 / 7%); }
:deep(.el-menu-item.is-active) { color: #fff; background: rgb(74 134 255 / 24%); font-weight: 600; }
:deep(.el-sub-menu .el-menu-item) { min-width: auto; padding-left: 48px !important; }
.pilot-note { display: flex; align-items: center; gap: 9px; margin: 12px; padding: 12px; color: var(--sidebar-muted); background: rgb(255 255 255 / 5%); border-radius: 9px; font-size: 12px; }
.pilot-dot { width: 7px; height: 7px; border-radius: 50%; background: #53d58a; box-shadow: 0 0 0 3px rgb(83 213 138 / 14%); }
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
  padding: 0 28px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}
.header-context { display: flex; align-items: baseline; gap: 10px; }
.header-context span { font-weight: 700; }
.header-context small { color: var(--ink-muted); }
.header-actions, .user-chip { display: flex; align-items: center; gap: 12px; }
.user-chip { gap: 8px; color: var(--ink-secondary); font-size: 13px; }
.avatar { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: var(--brand-strong); background: var(--brand-soft); font-weight: 700; }
.workspace { min-width: 0; padding: 0; overflow-x: hidden; overflow-y: auto; background: var(--app-bg); }

@media (max-width: 900px) {
  .aside { width: 76px !important; }
  .brand { justify-content: center; padding: 0; }
  .brand-copy, .nav-label, .pilot-note { display: none; }
  :deep(.el-menu-item), :deep(.el-sub-menu__title) { justify-content: center; padding: 0 !important; }
  :deep(.el-menu-item span), :deep(.el-sub-menu__title span), :deep(.el-sub-menu__icon-arrow) { display: none; }
  .header { padding: 0 20px; }
}
</style>
