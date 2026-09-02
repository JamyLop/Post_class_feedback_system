<template>
  <view class="page">
    <view class="banner">
      <text class="kicker">一生一案 · 高三试点</text>
      <text class="title">学业发展工作台</text>
      <text class="desc">先呈现状态与下一步行动，再展开完整材料</text>
      <view class="role-row">
        <text class="role-chip">{{ roleLabel }}</text>
        <text class="user-name">{{ auth.user?.name || '未登录' }}</text>
        <text v-if="!auth.isLoggedIn" class="login-tip" @click="goLogin">去登录 →</text>
      </view>
      <text v-if="roleHint" class="role-hint">{{ roleHint }}</text>
    </view>

    <view class="grid">
      <view
        v-for="entry in visibleEntries"
        :key="entry.key"
        class="entry"
        :class="{ disabled: entry.disabled }"
        @click="handleEntry(entry)"
      >
        <text class="entry-title">{{ entry.title }}</text>
        <text class="entry-desc">{{ entry.desc }}</text>
        <text class="entry-action">{{ entry.disabled ? entry.disabledText : '进入 →' }}</text>
      </view>
    </view>

    <view v-if="hiddenCount" class="hidden-tip">
      <text>已按角色隐藏 {{ hiddenCount }} 个非本角色入口，后端仍会拦截越权请求</text>
    </view>

    <view class="foot">
      <text class="foot-tip">DOCX 导出、批量导入、AI 草稿请在 Web 端完成</text>
      <button v-if="auth.isLoggedIn" plain size="mini" @click="handleLogout">退出登录</button>
      <button v-else type="primary" size="mini" @click="goLogin">账号密码登录</button>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const roleMap = { parent: '家长', student: '学生', teacher: '班主任', deyu_director: '德育主任', admin: '校长' }
const roleLabel = computed(() => roleMap[auth.role] || auth.role || '访客')
const roleHint = computed(() => {
  if (!auth.isLoggedIn) return '请先登录，登录后仅展示本角色可用入口'
  if (auth.role === 'parent') return '家长仅可查看已发布档案与任务，编辑请联系班主任'
  if (auth.role === 'student') return '学生仅可查看作业与本人已发布档案'
  if (['teacher', 'deyu_director', 'admin'].includes(auth.role)) return '支持档案查看/编辑、学科方案、任务管理、打卡与督查；DOCX 导出请在 Web 端'
  return ''
})

const allEntries = [
  { key: 'parent', roles: ['parent'], title: '家长 · 孩子档案', desc: '查看已发布总案、学科方案、任务与复盘', route: '/subParent/children/index' },
  { key: 'student', roles: ['student'], title: '学生 · 我的档案', desc: '查看本人一生一案档案、学科方案与任务', route: '/subStudent/myCase/index' },
  { key: 'teacher', roles: ['teacher', 'deyu_director', 'admin'], title: '教师 · 一生一案', desc: '待办概览、档案查看编辑、任务管理、打卡与督查', route: '/subTeacher/todo/index' },
]

const visibleEntries = computed(() => {
  // 未登录：全部展示，但点击会先去登录
  if (!auth.isLoggedIn || !auth.role) {
    return allEntries.map(e => ({ ...e, disabled: false, disabledText: '' }))
  }
  const allowed = allEntries.filter(e => e.roles.includes(auth.role))
  const disallowed = allEntries.filter(e => !e.roles.includes(auth.role))
  // 已登录：仅可用入口可点击，其余置灰并提示无权限
  return [
    ...allowed.map(e => ({ ...e, disabled: false, disabledText: '' })),
    ...disallowed.map(e => ({ ...e, disabled: true, disabledText: '当前角色不可用' })),
  ]
})
const hiddenCount = computed(() => {
  if (!auth.isLoggedIn || !auth.role) return 0
  return allEntries.filter(e => !e.roles.includes(auth.role)).length
})

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }
function handleEntry(entry) {
  if (!auth.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return goLogin()
  }
  if (entry.disabled) {
    uni.showToast({ title: '当前角色无权限访问该入口', icon: 'none' })
    return
  }
  uni.navigateTo({ url: entry.route })
}
function handleLogout() { auth.logout() }
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:24rpx; }
.banner { background:#0f172a; color:#fff; border-radius:16rpx; padding:32rpx 28rpx; }
.kicker { font-size:20rpx; color:#94a3b8; }
.title { font-size:34rpx; font-weight:700; display:block; margin-top:8rpx; }
.desc { font-size:24rpx; color:#94a3b8; display:block; margin-top:6rpx; }
.role-row { margin-top:18rpx; display:flex; gap:12rpx; align-items:center; }
.role-chip { font-size:20rpx; padding:6rpx 14rpx; border-radius:999rpx; background:#1e293b; color:#93c5fd; border:1rpx solid rgba(255,255,255,0.08); }
.user-name { font-size:26rpx; font-weight:600; }
.login-tip { font-size:22rpx; color:#93c5fd; margin-left:8rpx; text-decoration:underline; }
.role-hint { font-size:22rpx; color:#94a3b8; display:block; margin-top:10rpx; line-height:1.5; }
.grid { display:flex; flex-direction:column; gap:16rpx; }
.entry { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:28rpx; }
.entry.disabled { background:#f8fafc; opacity:0.6; }
.entry-title { font-size:28rpx; font-weight:600; color:#0f172a; display:block; }
.entry-desc { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; line-height:1.5; }
.entry-action { font-size:24rpx; color:#2563eb; display:block; margin-top:12rpx; font-weight:500; }
.entry.disabled .entry-action { color:#94a3b8; }
.hidden-tip { font-size:20rpx; color:#94a3b8; text-align:center; }
.foot { text-align:center; display:flex; flex-direction:column; gap:16rpx; align-items:center; }
.foot-tip { font-size:22rpx; color:#94a3b8; }
</style>
