<template>
  <view class="page admin-page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">系统管理</text>
      <text class="p">查看全校数据，管理账号与班级</text>
    </view>

    <view class="overview">
      <text class="section-title">数据概览</text>
      <view v-if="loading" class="loading-bar">
        <text class="loading-text">正在读取统计数据…</text>
      </view>
      <view v-else class="stats-grid">
        <view class="stat-card" v-for="s in statItems" :key="s.key">
          <text class="stat-num">{{ stats[s.key] || 0 }}</text>
          <text class="stat-label">{{ s.label }}</text>
        </view>
      </view>
    </view>

    <view class="management">
      <text class="section-title">管理功能</text>
      <view class="nav-list">
        <button class="nav-row" hover-class="nav-row-active" @click="goUsers">
          <view class="nav-copy"><text class="nav-title">用户管理</text><text class="nav-desc">查看、创建与禁用用户</text></view>
          <text class="nav-arrow" aria-hidden="true">›</text>
        </button>
        <button class="nav-row" hover-class="nav-row-active" @click="goInviteCodes">
          <view class="nav-copy"><text class="nav-title">邀请码</text><text class="nav-desc">生成与停用注册邀请码</text></view>
          <text class="nav-arrow" aria-hidden="true">›</text>
        </button>
        <button class="nav-row" hover-class="nav-row-active" @click="goClasses">
          <view class="nav-copy"><text class="nav-title">班级管理</text><text class="nav-desc">管理班级信息与学生名单</text></view>
          <text class="nav-arrow" aria-hidden="true">›</text>
        </button>
        <button class="nav-row" hover-class="nav-row-active" @click="goCaseList">
          <view class="nav-copy"><text class="nav-title">全部档案</text><text class="nav-desc">查看全校学生的一生一案</text></view>
          <text class="nav-arrow" aria-hidden="true">›</text>
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getAdminStats } from '../../api/studentCases'

const auth = useAuthStore()
const loading = ref(false)
const stats = ref({})

const statItems = [
  { key: 'user_count', label: '总用户' },
  { key: 'teacher_count', label: '教师' },
  { key: 'student_count', label: '学生' },
  { key: 'parent_count', label: '家长' },
  { key: 'deyu_director_count', label: '德育主任' },
  { key: 'class_count', label: '班级' },
  { key: 'case_count', label: '一生一案' },
]

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'admin') {
    uni.showToast({ title: '仅校长可访问' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function load() {
  loading.value = true
  try { stats.value = await getAdminStats() } catch (_) { stats.value = {} } finally { loading.value = false }
}

function goUsers() { uni.navigateTo({ url: '/subTeacher/adminUsers/index' }) }
function goInviteCodes() { uni.navigateTo({ url: '/subTeacher/adminUsers/index?tab=invite' }) }
function goClasses() { uni.navigateTo({ url: '/subTeacher/classManager/index' }) }
function goCaseList() { uni.navigateTo({ url: '/subTeacher/caseList/index' }) }

onShow(() => { if (guardRole()) load() })
</script>

<style scoped>
.admin-page { box-sizing: border-box; width: 100%; min-width: 0; padding: 24rpx 32rpx calc(40rpx + env(safe-area-inset-bottom)); display: flex; flex-direction: column; gap: 28rpx; }
.head { padding: 4rpx 0; }
.h1 { display: block; font-size: 38rpx; font-weight: 600; color: var(--mp-ink); }
.p { display: block; margin-top: 8rpx; font-size: 25rpx; color: var(--mp-muted); }
.section-title { display: block; font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.overview { background: var(--mp-surface); border-radius: 16rpx; padding: 24rpx 0 8rpx; }
.overview > .section-title { padding: 0 24rpx 12rpx; }
/* 显式包含内边距，四等分不依赖全局元素选择器，避免小程序端换行后留下半屏空白。 */
.stats-grid { display: flex; flex-wrap: wrap; width: 100%; }
.stat-card { box-sizing: border-box; flex: 0 0 25%; width: 25%; min-width: 0; padding: 16rpx 8rpx 20rpx; text-align: center; }
.stat-card:nth-child(n + 5) { border-top: 1rpx solid var(--mp-line); }
.stat-num { display: block; font-size: 36rpx; line-height: 1.3; font-weight: 600; color: var(--mp-ink); overflow-wrap: anywhere; }
.stat-label { display: block; margin-top: 8rpx; font-size: 23rpx; color: var(--mp-muted); }
.loading-bar { padding: 48rpx 24rpx; text-align: center; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.management > .section-title { margin-bottom: 16rpx; }
.nav-list { background: var(--mp-surface); border-radius: 16rpx; overflow: hidden; }
.nav-row { box-sizing: border-box; display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 132rpx; margin: 0; padding: 24rpx; border: 0; border-radius: 0; background: transparent; text-align: left; line-height: 1.5; }
.nav-row + .nav-row { border-top: 1rpx solid var(--mp-line); }
.nav-row::after { border: none; }
.nav-row-active { background: var(--mp-soft); }
.nav-copy { flex: 1; min-width: 0; }
.nav-title { display: block; font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.nav-desc { display: block; margin-top: 6rpx; font-size: 24rpx; color: var(--mp-muted); }
.nav-arrow { flex-shrink: 0; margin-left: 20rpx; font-size: 40rpx; font-weight: 400; color: var(--mp-muted); }
</style>
