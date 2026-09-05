<template>
  <view class="page">
    <view class="banner">
      <view class="banner-bg"></view>
      <view class="banner-content">
        <text class="banner-badge">一生一案 · 高三试点</text>
        <text class="banner-title">学业发展工作台</text>
        <view class="user-row">
          <view class="avatar" :style="{ background: avatarColor }">
            <text class="avatar-text">{{ (auth.user?.name || '?').slice(0, 1) }}</text>
          </view>
          <view class="user-info">
            <text class="user-name">{{ auth.user?.name || '未登录' }}</text>
            <text class="user-role">{{ roleLabel }}</text>
          </view>
          <text v-if="!auth.isLoggedIn" class="login-btn" @click="goLogin">登录</text>
        </view>
        <text v-if="roleHint" class="role-hint">{{ roleHint }}</text>
      </view>
    </view>

    <view class="section">
      <text class="section-label">功能入口</text>
      <view class="grid">
        <view
          v-for="entry in visibleEntries"
          :key="entry.key"
          class="entry-card"
          :class="{ 'is-disabled': entry.disabled }"
          @click="handleEntry(entry)"
        >
          <view class="entry-mark" :class="`mark-${entry.key}`"></view>
          <view class="entry-body">
            <text class="entry-title">{{ entry.title }}</text>
            <text class="entry-desc">{{ entry.desc }}</text>
          </view>
          <text class="entry-arrow" :class="{ 'is-disabled': entry.disabled }">
            {{ entry.disabled ? '·' : '›' }}
          </text>
        </view>
      </view>
    </view>

    <view v-if="hiddenCount" class="hidden-bar">
      <text class="hidden-text">已按角色隐藏 {{ hiddenCount }} 个入口</text>
    </view>

    <view class="bottom-bar">
      <text class="bottom-tip">DOCX 导出、批量导入请在 Web 端完成</text>
      <button v-if="auth.isLoggedIn" class="btn-logout" plain @click="handleLogout">退出登录</button>
      <button v-else class="btn-login" @click="goLogin">账号密码登录</button>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const roleMap = { parent: '家长', student: '学生', teacher: '班主任', deyu_director: '德育主任', admin: '校长', consultant: '咨询老师', subject_teacher: '任课老师' }
const roleLabel = computed(() => roleMap[auth.role] || auth.role || '访客')

const avatarColors = ['#6B5CE7', '#F5881F', '#16A34A', '#E74C6F', '#3B82F6']
const avatarColor = computed(() => {
  const idx = (auth.user?.name || '').charCodeAt(0) % avatarColors.length
  return avatarColors[idx]
})

const roleHint = computed(() => {
  if (!auth.isLoggedIn) return '请先登录，登录后仅展示本角色可用入口'
  if (auth.role === 'parent') return '可查看已发布档案与任务'
  if (auth.role === 'student') return '查看本人已发布档案'
  if (auth.role === 'teacher') return '档案编辑、任务管理、打卡与督查'
  if (auth.role === 'deyu_director') return '审查方案、查看督查进度'
  if (auth.role === 'admin') return '系统统计、用户管理、全局档案'
  if (auth.role === 'consultant') return '查看关联学生档案，了解学情动态'
  if (auth.role === 'subject_teacher') return '查看所带班级档案，提交学科建议'
  return ''
})

const allEntries = [
  { key: 'parent', roles: ['parent'], title: '孩子档案', desc: '查看已发布总案与学科方案', route: '/subParent/children/index' },
  { key: 'student_case', roles: ['student'], title: '我的档案', desc: '查看本人一生一案', route: '/pages/student/myCase/index' },
  { key: 'student_monthly', roles: ['student'], title: '月度评价', desc: '查看老师发布的月度评价', route: '/pages/student/monthlyReports/index' },
  { key: 'student_profile', roles: ['student'], title: '个人信息', desc: '查看个人基本信息', route: '/pages/student/profile/index' },
  { key: 'student_analytics', roles: ['student'], title: '学情分析', desc: '查看个人学情分析', route: '/pages/student/analytics/index' },
  { key: 'teacher', roles: ['teacher'], title: '工作台', desc: '待办、档案编辑、打卡', route: '/subTeacher/todo/index' },
  { key: 'teacher_weekly', roles: ['teacher'], title: '周测成绩', desc: '录入与查看班级周测成绩', route: '/subTeacher/weeklyScores/index' },
  { key: 'teacher_monthly', roles: ['teacher'], title: '月度评价', desc: 'AI 生成学生月度评价', route: '/subTeacher/monthlyReports/index' },
  { key: 'teacher_class', roles: ['teacher'], title: '班级管理', desc: '管理班级与学生信息', route: '/subTeacher/classManager/index' },
  { key: 'deyu_director', roles: ['deyu_director'], title: '审查中心', desc: '方案审查与督查进度', route: '/subTeacher/todo/index' },
  { key: 'admin', roles: ['admin'], title: '系统管理', desc: '统计、用户、邀请码', route: '/subTeacher/todo/index' },
  { key: 'consultant', roles: ['consultant'], title: '关联学生', desc: '查看所负责学生的档案', route: '/subConsultant/caseList/index' },
  { key: 'subject_teacher', roles: ['subject_teacher'], title: '我的课程档案', desc: '查看所带班级学生档案', route: '/subTeacher/caseList/index' },
]

const visibleEntries = computed(() => {
  if (!auth.isLoggedIn || !auth.role) {
    return allEntries.map(e => ({ ...e, disabled: false }))
  }
  const allowed = allEntries.filter(e => e.roles.includes(auth.role))
  const disallowed = allEntries.filter(e => !e.roles.includes(auth.role))
  return [
    ...allowed.map(e => ({ ...e, disabled: false })),
    ...disallowed.map(e => ({ ...e, disabled: true })),
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
    uni.showToast({ title: '当前角色无权限', icon: 'none' })
    return
  }
  uni.navigateTo({ url: entry.route })
}
function handleLogout() { auth.logout() }
</script>

<style scoped>
.page { padding: 0 28rpx 48rpx; display: flex; flex-direction: column; gap: 24rpx; }

.banner {
  position: relative;
  border-radius: 12rpx;
  overflow: hidden;
  margin-top: 16rpx;
}
.banner-bg {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: #1F4F55;
}
.banner-content { position: relative; padding: 36rpx 28rpx 28rpx; }
.banner-badge {
  font-size: 22rpx;
  color: #DDEBE8;
  padding: 0;
  display: inline-block;
  font-weight: 500;
}
.banner-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #fff;
  display: block;
  margin-top: 18rpx;
}
.user-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
  margin-top: 20rpx;
}
.avatar {
  width: 68rpx; height: 68rpx;
  border-radius: 18rpx;
  display: flex; align-items: center; justify-content: center;
}
.avatar-text { color: #fff; font-size: 28rpx; font-weight: 700; }
.user-info { flex: 1; }
.user-name { font-size: 28rpx; font-weight: 600; color: #fff; display: block; }
.user-role { font-size: 22rpx; color: rgba(255,255,255,0.65); display: block; margin-top: 2rpx; }
.login-btn {
  font-size: 24rpx;
  color: #1F4F55;
  background: #F3C969;
  padding: 12rpx 28rpx;
  border-radius: 8rpx;
  font-weight: 600;
}
.role-hint {
  font-size: 22rpx;
  color: #C5DBD7;
  display: block;
  margin-top: 14rpx;
  line-height: 1.5;
}

.section { display: flex; flex-direction: column; gap: 14rpx; }
.section-label { font-size: 25rpx; font-weight: 600; color: #53666A; padding-left: 2rpx; }

.grid { display: flex; flex-direction: column; gap: 14rpx; }

.entry-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  background: #fff;
  border-radius: 10rpx;
  padding: 26rpx 22rpx;
  border: 1rpx solid #E0E7E5;
}
.entry-card.is-disabled {
  opacity: 0.45;
}
.entry-mark {
  width: 8rpx; height: 52rpx;
  border-radius: 4rpx;
  background: #1F4F55;
  flex-shrink: 0;
}
.mark-student { background: #4C7A64; }
.mark-teacher { background: #427B87; }
.mark-deyu_director { background: #B47D37; }
.mark-admin { background: #7E5C58; }
.mark-consultant { background: #8B5CF6; }
.mark-subject_teacher { background: #0EA5E9; }
.entry-body { flex: 1; }
.entry-title { font-size: 29rpx; font-weight: 600; color: #203235; display: block; }
.entry-desc { font-size: 23rpx; color: #6C7C7F; display: block; margin-top: 6rpx; }
.entry-arrow {
  font-size: 32rpx;
  color: #739095;
  font-weight: 600;
  flex-shrink: 0;
}
.entry-arrow.is-disabled { color: #C4C0D4; }

.hidden-bar {
  text-align: center;
  padding: 12rpx;
}
.hidden-text { font-size: 22rpx; color: #A09CB5; }

.bottom-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
  padding-top: 8rpx;
}
.bottom-tip { font-size: 22rpx; color: #899799; }
.btn-logout {
  font-size: 24rpx;
  color: #53666A;
  border: 1rpx solid #CBD6D4;
  border-radius: 8rpx;
  padding: 10rpx 32rpx;
  background: #fff;
}
.btn-login {
  background: #1F4F55;
  color: #fff;
  font-size: 28rpx;
  font-weight: 600;
  border-radius: 8rpx;
  padding: 18rpx 0;
  border: none;
}
.btn-login::after { border: none; }
</style>
