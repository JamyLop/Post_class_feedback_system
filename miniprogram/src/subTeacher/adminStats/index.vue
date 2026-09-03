<template>
  <view class="page">
    <view class="head">
      <text class="h1">系统管理</text>
      <text class="p">校长专属：系统概览、用户管理、邀请码</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view class="stats-grid">
        <view class="stat-card" v-for="s in statItems" :key="s.key">
          <view class="stat-icon" :style="{ background: s.bg }"><text>{{ s.icon }}</text></view>
          <text class="stat-num">{{ stats[s.key] || 0 }}</text>
          <text class="stat-label">{{ s.label }}</text>
        </view>
      </view>

      <view class="nav-grid">
        <view class="nav-card" @click="goUsers">
          <text class="nav-icon">👥</text>
          <text class="nav-title">用户管理</text>
          <text class="nav-desc">查看/创建/禁用用户</text>
        </view>
        <view class="nav-card" @click="goInviteCodes">
          <text class="nav-icon">🎟️</text>
          <text class="nav-title">邀请码</text>
          <text class="nav-desc">生成/停用注册邀请码</text>
        </view>
        <view class="nav-card" @click="goClasses">
          <text class="nav-icon">🏫</text>
          <text class="nav-title">班级管理</text>
          <text class="nav-desc">创建/编辑班级与学生</text>
        </view>
        <view class="nav-card" @click="goCaseList">
          <text class="nav-icon">📚</text>
          <text class="nav-title">全部档案</text>
          <text class="nav-desc">全局学生档案查看</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getAdminStats } from '../../api/studentCases'

const auth = useAuthStore()
const loading = ref(false)
const stats = ref({})

const statItems = [
  { key: 'user_count', label: '总用户', icon: '👥', bg: 'linear-gradient(135deg,#EEEDFD,#DDD6FE)' },
  { key: 'teacher_count', label: '教师', icon: '👩‍🏫', bg: 'linear-gradient(135deg,#DBEAFE,#BFDBFE)' },
  { key: 'student_count', label: '学生', icon: '📖', bg: 'linear-gradient(135deg,#D1FAE5,#BBF7D0)' },
  { key: 'parent_count', label: '家长', icon: '👨‍👩‍👧', bg: 'linear-gradient(135deg,#FEF3CD,#FDE68A)' },
  { key: 'deyu_director_count', label: '德育主任', icon: '🔍', bg: 'linear-gradient(135deg,#F3E8FF,#DDD6FE)' },
  { key: 'class_count', label: '班级', icon: '🏫', bg: 'linear-gradient(135deg,#FFE4D6,#FED7AA)' },
  { key: 'case_count', label: '一生一案', icon: '📋', bg: 'linear-gradient(135deg,#EEF2FF,#C7D2FE)' },
  { key: 'assignment_count', label: '作业', icon: '📝', bg: 'linear-gradient(135deg,#F0FDF4,#BBF7D0)' },
]

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'admin') {
    uni.showToast({ title: '仅校长可访问', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function load() {
  loading.value = true
  try { stats.value = await getAdminStats() } catch (_) { stats.value = {} } finally { loading.value = false }
}

function goUsers() { uni.navigateTo({ url: '/subTeacher/adminUsers/index' }) }
function goInviteCodes() { uni.navigateTo({ url: '/subTeacher/adminUsers/index?tab=invite' }) }
function goClasses() { uni.navigateTo({ url: '/subTeacher/caseList/index' }) }
function goCaseList() { uni.navigateTo({ url: '/subTeacher/caseList/index' }) }

onShow(() => { if (guardRole()) load() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.head { margin-bottom: 4rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.stats-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.stat-card {
  width: calc(50% - 7rpx);
  background: #fff;
  border-radius: 18rpx;
  padding: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(107,92,231,0.05);
}
.stat-icon {
  width: 56rpx; height: 56rpx;
  border-radius: 14rpx;
  display: flex; align-items: center; justify-content: center;
  font-size: 24rpx; margin-bottom: 12rpx;
}
.stat-num { font-size: 36rpx; font-weight: 700; color: #1A1636; display: block; }
.stat-label { font-size: 20rpx; color: #8E8B9E; display: block; margin-top: 2rpx; }

.nav-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.nav-card {
  width: calc(50% - 7rpx);
  background: #fff;
  border-radius: 18rpx;
  padding: 22rpx;
  box-shadow: 0 2rpx 12rpx rgba(107,92,231,0.05);
}
.nav-icon { font-size: 36rpx; display: block; margin-bottom: 10rpx; }
.nav-title { font-size: 28rpx; font-weight: 600; color: #1A1636; display: block; }
.nav-desc { font-size: 22rpx; color: #8E8B9E; display: block; margin-top: 4rpx; }
</style>
