<template>
  <view class="page home-page">
    <view class="masthead"><text class="brand">一生一案</text><text class="edition">高三学业发展</text></view>
    <view class="welcome">
      <view class="welcome-copy"><text class="welcome-title">{{ auth.isLoggedIn ? `${auth.user?.name || '您好'}，您好` : '欢迎使用' }}</text><text class="welcome-desc">{{ roleHint }}</text></view>
      <view class="identity"><text>{{ roleLabel }}</text></view>
    </view>
    <template v-if="auth.isLoggedIn && primaryEntry">
      <view class="focus-panel" hover-class="focus-active" @click="openEntry(primaryEntry)">
        <text class="focus-label">{{ primaryLabel }}</text>
        <view class="focus-main"><text class="focus-title">{{ primaryEntry.title }}</text><text class="focus-arrow">↗</text></view>
        <text class="focus-desc">{{ primaryEntry.desc }}</text>
        <view class="focus-footer"><text>{{ primaryHint }}</text><text>进入 ›</text></view>
      </view>
      <view v-for="group in groups" :key="group.title" class="section">
        <view class="section-heading"><text class="section-title">{{ group.title }}</text></view>
        <view class="entry-list">
          <button v-for="entry in group.entries" :key="entry.route" class="entry" hover-class="tap-active" @click="openEntry(entry)">
            <view class="entry-copy"><text class="entry-title">{{ entry.title }}</text><text class="entry-desc">{{ entry.desc }}</text></view><text class="entry-arrow">›</text>
          </button>
        </view>
      </view>
      <view class="account-row"><text>{{ roleLabel }} · {{ auth.user?.username || auth.user?.name }}</text><button class="logout" @click="auth.logout()">退出登录</button></view>
    </template>
    <view v-else class="guest-panel">
      <text class="guest-title">从这里开始您的工作</text><text class="guest-desc">登录后查看与您相关的学生档案、教学记录和待办事项。</text>
      <button class="login" @click="goLogin">登录账号</button>
    </view>
  </view>
</template>
<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { ROLE_LABELS, entriesForRole, groupsForRole } from '../../utils/navigation'
const auth = useAuthStore()
const roleLabel = computed(() => ROLE_LABELS[auth.role] || '访客')
const primaryEntry = computed(() => entriesForRole(auth.role)[0])
const groups = computed(() => groupsForRole(auth.role).map(group => ({ ...group, entries: group.entries.filter(entry => entry.route !== primaryEntry.value?.route) })).filter(group => group.entries.length))
const roleHint = computed(() => ({ teacher: '学生的目标、方案与进展，都在这里。', student: '了解当前目标，查看每一阶段的学习记录。', parent: '关注孩子的成长，与老师保持同一步调。', deyu_director: '跟进方案审查与整改落实。', admin: '掌握全校档案进展与教学管理情况。', subject_teacher: '查阅学科方案，记录有依据的教学建议。', consultant: '持续了解所负责学生的学业进展。' }[auth.role] || '连接学校、教师与家庭的学业发展记录。'))
const primaryLabel = computed(() => ['teacher', 'admin', 'deyu_director'].includes(auth.role) ? '工作概览' : '成长档案')
const primaryHint = computed(() => ['parent', 'student'].includes(auth.role) ? '以老师发布的版本为准' : '关注当前状态，跟进下一步工作')
function openEntry(entry) { if (!auth.isLoggedIn) return goLogin(); uni.navigateTo({ url: entry.route }) }
function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }
</script>
<style scoped>
.page { padding: 32rpx 32rpx calc(40rpx + env(safe-area-inset-bottom)); }
.masthead { display: flex; align-items: center; justify-content: space-between; padding: 12rpx 0 28rpx; border-bottom: 1rpx solid var(--mp-line); }
.brand { font-size: 32rpx; font-weight: 700; letter-spacing: 3rpx; }.edition { font-size: 23rpx; color: var(--mp-muted); }
.welcome { display: flex; gap: 20rpx; align-items: flex-start; padding: 36rpx 0 32rpx; }.welcome-copy { flex: 1; min-width: 0; }
.welcome-title { display: block; font-size: 38rpx; font-weight: 600; overflow-wrap: anywhere; }.welcome-desc { display: block; margin-top: 12rpx; font-size: 25rpx; color: var(--mp-muted); line-height: 1.7; }
.identity { flex-shrink: 0; padding: 8rpx 16rpx; border: 1rpx solid #C6D0DE; border-radius: 6rpx; color: var(--mp-body); font-size: 23rpx; margin-top: 8rpx; }
.focus-panel { padding: 30rpx; background: var(--mp-primary); color: white; border-radius: 16rpx; }.focus-active { background: #1C304F; }
.focus-label { font-size: 23rpx; color: #D5DEEB; }.focus-main { display: flex; justify-content: space-between; align-items: center; margin-top: 16rpx; }.focus-title { font-size: 38rpx; font-weight: 600; }.focus-arrow { font-size: 36rpx; color: #D5DEEB; }
.focus-desc { display: block; color: #D5DEEB; font-size: 25rpx; margin-top: 10rpx; }.focus-footer { margin-top: 28rpx; padding-top: 20rpx; border-top: 1rpx solid #526887; display: flex; justify-content: space-between; gap: 16rpx; font-size: 23rpx; color: #E4EAF3; }
.section { margin-top: 34rpx; }.section-heading { margin-bottom: 16rpx; }.section-title { font-size: 27rpx; font-weight: 600; }
.entry-list { background: white; border-radius: 16rpx; padding: 0 28rpx; }.entry { width: 100%; display: flex; align-items: center; gap: 20rpx; text-align: left; background: transparent; border-radius: 0; padding: 27rpx 0; }.entry + .entry { border-top: 1rpx solid var(--mp-line); }.entry-copy { flex: 1; min-width: 0; }.entry-title { display: block; font-size: 29rpx; color: var(--mp-ink); font-weight: 500; }.entry-desc { display: block; font-size: 24rpx; color: var(--mp-muted); margin-top: 8rpx; line-height: 1.55; }.entry-arrow { color: var(--mp-muted); font-size: 34rpx; }
.account-row { margin-top: 34rpx; display: flex; align-items: center; justify-content: space-between; gap: 20rpx; color: var(--mp-muted); font-size: 23rpx; }.logout { flex-shrink: 0; background: transparent; color: var(--mp-body); font-size: 24rpx; padding: 20rpx 0 20rpx 20rpx; }
.guest-panel { padding: 36rpx; background: white; border-radius: 16rpx; }.guest-title { display: block; font-size: 30rpx; font-weight: 600; }.guest-desc { display: block; margin-top: 16rpx; color: var(--mp-muted); font-size: 26rpx; }.login { margin-top: 32rpx; background: var(--mp-primary); color: white; padding: 24rpx; font-size: 28rpx; border-radius: 10rpx; }
</style>
