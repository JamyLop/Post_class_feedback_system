<template>
  <el-container class="app-shell">
    <el-aside width="228px" class="aside">
      <div class="brand">
        <div class="brand-mark">案</div>
        <div class="brand-copy">
          <strong>一生一案</strong>
          <span>学业发展管理</span>
        </div>
      </div>

        <el-scrollbar class="nav-scroll">
        <div class="nav-label">教学管理</div>
        <el-menu :default-active="activeMenu" router>
          <template v-for="item in menuItems" :key="item.index">
            <el-menu-item :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="aside-foot">
        <span>高三备考 · 2026-2027</span>
      </div>
    </el-aside>

    <el-container class="main-container">
      <el-header class="header">
        <div class="header-left">
          <span class="role-title">{{ auth.role === 'deyu_director' ? '德育主任工作台' : auth.role === 'admin' ? '校级工作台' : '班主任工作台' }}</span>
          <span class="context-tag">{{ pageContext }}</span>
        </div>
        <div class="header-right">
          <div class="user-profile">
            <span class="avatar-badge">{{ auth.user?.name?.slice(0, 1) || '用' }}</span>
            <div class="user-meta">
              <strong class="user-name">{{ auth.user?.name || '教师' }}</strong>
              <small class="user-role-text">{{ auth.role === 'deyu_director' ? '德育主任' : auth.role === 'admin' ? '校长' : '班主任' }}</small>
            </div>
          </div>
          <div class="divider"></div>
          <el-button link class="logout-btn" @click="onLogout">退出</el-button>
        </div>
      </el-header>

      <el-main ref="workspaceRef" class="workspace">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Bell, DataAnalysis, Files, Notebook, School, TrendCharts } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const workspaceRef = ref(null)

const activeMenu = computed(() => route.path)

const menuItems = computed(() => {
  const role = auth.role
  const allItems = [
    { index: '/teacher/student-cases', icon: 'Files', title: '学生档案', roles: ['admin', 'teacher', 'deyu_director'] },
    { index: '/teacher/weekly-scores', icon: 'DataAnalysis', title: '周测成绩', roles: ['admin', 'teacher'] },
    { index: '/teacher/task-reminders', icon: 'Bell', title: '任务提醒', roles: ['admin', 'teacher'] },
    { index: '/teacher/points-reports', icon: 'TrendCharts', title: '积分周月报', roles: ['admin', 'teacher'] },
    { index: '/teacher/monthly-reports', icon: 'Notebook', title: '月度评定', roles: ['admin', 'teacher'] },
    { index: '/teacher/classes', icon: 'School', title: '班级与教师', roles: ['admin', 'teacher'] },
  ]
  return allItems.filter(item => item.roles.includes(role))
})

const pageContext = computed(() => {
  if (route.path.includes('/student-cases/')) return '档案详情'
  if (route.path === '/teacher/student-cases') return '档案库'
  if (route.path === '/teacher/weekly-scores') return '周测'
  if (route.path === '/teacher/task-reminders') return '任务提醒'
  if (route.path === '/teacher/points-reports') return '积分周月报'
  if (route.path === '/teacher/monthly-reports') return '月度评定'
  if (route.path === '/teacher/classes') return '班级'
  return '教学'
})

watch(
  () => route.fullPath,
  async () => {
    await nextTick()
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
.app-shell {
  height: 100vh;
  min-width: 0;
  overflow: hidden;
  background: var(--app-bg);
}

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
  background: #2f5bff;
  font-weight: 700;
  font-size: 14px;
}

.brand-copy {
  display: grid;
  gap: 1px;
}

.brand-copy strong {
  color: #e8ecf3;
  font-size: 13.5px;
  font-weight: 600;
}

.brand-copy span {
  color: #6b778d;
  font-size: 11px;
}

.nav-scroll {
  flex: 1;
  padding: 14px 0 8px;
}

.nav-label {
  padding: 6px 18px 8px;
  color: #5a6782;
  font-size: 11px;
  font-weight: 500;
}

:deep(.el-menu) {
  border-right: 0;
  background: transparent;
}

:deep(.el-menu-item) {
  height: 38px;
  margin: 1px 8px;
  padding: 0 12px !important;
  border-radius: 8px;
  color: #8a97ad;
  font-size: 13.5px;
}

:deep(.el-menu-item:hover) {
  color: #d6deeb;
  background: rgba(255, 255, 255, 0.05);
}

:deep(.el-menu-item.is-active) {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
  font-weight: 600;
  position: relative;
}

:deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2.5px;
  border-radius: 999px;
  background: #5b7cff;
}

:deep(.el-menu-item .el-icon) {
  font-size: 15px;
  margin-right: 9px;
}

.aside-foot {
  padding: 12px 16px;
  border-top: 1px solid var(--side-line);
  font-size: 11px;
  color: #5a6782;
}

.main-container {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
  padding: 0 20px 0 22px;
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-title {
  font-weight: 650;
  font-size: 14px;
  color: var(--ink);
}

.context-tag {
  font-size: 11.5px;
  color: #5b667a;
  background: #f2f3f5;
  border: 1px solid #e6e8eb;
  padding: 2px 7px;
  border-radius: 6px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 9px;
}

.avatar-badge {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: #eef2ff;
  color: #2f5bff;
  border: 1px solid #dfe6ff;
  display: grid;
  place-items: center;
  font-weight: 600;
  font-size: 12.5px;
}

.user-meta {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 12.5px;
  color: var(--ink);
  font-weight: 600;
  line-height: 1.2;
}

.user-role-text {
  font-size: 11px;
  color: var(--ink-muted);
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

.workspace {
  flex: 1;
  min-width: 0;
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--app-bg);
}

@media (max-width: 900px) {
  .aside { width: 60px !important; }
  .brand-copy, .nav-label, .aside-foot, .user-meta { display: none; }
  .brand { justify-content: center; padding: 0; }
  :deep(.el-menu-item) { justify-content: center; padding: 0 !important; margin: 1px 6px; }
  :deep(.el-menu-item span) { display: none; }
  :deep(.el-menu-item .el-icon) { margin-right: 0; }
  .header { padding: 0 12px; }
}
</style>
