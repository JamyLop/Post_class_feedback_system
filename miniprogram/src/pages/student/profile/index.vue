<template>
  <view class="page">
    <view class="head">
      <text class="h1">个人信息</text>
      <text class="p">查看个人基本信息</text>
      <button class="refresh-btn" @click="loadProfile" :loading="loading">刷新</button>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="user">
      <!-- 头像区域 -->
      <view class="avatar-card">
        <view class="avatar" :style="{ background: avatarColor }">
          <text class="avatar-text">{{ (user.name || '?').slice(0, 1) }}</text>
        </view>
        <view class="avatar-info">
          <text class="user-name">{{ user.name }}</text>
          <text class="user-role">学生</text>
        </view>
      </view>

      <!-- 基本信息 -->
      <view class="card">
        <text class="card-title">基本信息</text>
        <view class="info-list">
          <view class="info-row">
            <text class="info-label">用户名</text>
            <text class="info-value">{{ user.username }}</text>
          </view>
          <view class="info-row has-border">
            <text class="info-label">姓名</text>
            <text class="info-value">{{ user.name }}</text>
          </view>
          <view class="info-row has-border">
            <text class="info-label">性别</text>
            <text class="info-value">{{ user.gender || '未填写' }}</text>
          </view>
          <view class="info-row has-border">
            <text class="info-label">民族</text>
            <text class="info-value">{{ user.ethnicity || '未填写' }}</text>
          </view>
          <view class="info-row has-border">
            <text class="info-label">年级</text>
            <text class="info-value">{{ user.grade || '未填写' }}</text>
          </view>
          <view class="info-row has-border">
            <text class="info-label">生源学校</text>
            <text class="info-value">{{ user.source_school || '未填写' }}</text>
          </view>
        </view>
      </view>

      <!-- 账号状态 -->
      <view class="card">
        <text class="card-title">账号信息</text>
        <view class="info-list">
          <view class="info-row">
            <text class="info-label">账号状态</text>
            <view class="status-tag" :class="user.status === 'active' ? 'is-active' : 'is-disabled'">
              <text class="status-text">{{ user.status === 'active' ? '正常' : '已禁用' }}</text>
            </view>
          </view>
          <view class="info-row has-border">
            <text class="info-label">角色</text>
            <text class="info-value">学生</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../../stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const user = ref(null)

const avatarColors = ['#6B5CE7', '#F5881F', '#16A34A', '#E74C6F', '#3B82F6']
const avatarColor = computed(() => {
  const idx = (user.value?.name || '').charCodeAt(0) % avatarColors.length
  return avatarColors[idx]
})

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'student') {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadProfile() {
  loading.value = true
  try {
    await auth.refreshMe()
    user.value = auth.user
  } catch (e) {
    user.value = auth.user
  } finally {
    loading.value = false
  }
}

onShow(() => {
  if (guardRole()) {
    user.value = auth.user
    loadProfile()
  }
})
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }
.refresh-btn {
  align-self: flex-start; font-size: 22rpx; color: #6B5CE7;
  background: #F0EFFC; border: none; border-radius: 10rpx;
  padding: 8rpx 20rpx; margin-top: 4rpx;
}
.refresh-btn::after { border: none; }

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.avatar-card {
  background: #1F4F55; border-radius: 16rpx;
  padding: 32rpx; display: flex; align-items: center; gap: 20rpx;
}
.avatar {
  width: 96rpx; height: 96rpx; border-radius: 24rpx;
  display: flex; align-items: center; justify-content: center;
}
.avatar-text { color: #fff; font-size: 40rpx; font-weight: 700; }
.avatar-info { flex: 1; }
.user-name { font-size: 34rpx; font-weight: 700; color: #fff; display: block; }
.user-role { font-size: 24rpx; color: rgba(255,255,255,0.7); display: block; margin-top: 6rpx; }

.card {
  background: #fff; border-radius: 12rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; margin-bottom: 14rpx; }

.info-list { display: flex; flex-direction: column; }
.info-row { padding: 16rpx 0; display: flex; align-items: center; justify-content: space-between; }
.info-row.has-border { border-top: 2rpx solid #F0EFFC; }
.info-label { font-size: 26rpx; color: #6E6B83; }
.info-value { font-size: 26rpx; color: #1A1636; font-weight: 500; }

.status-tag { padding: 4rpx 14rpx; border-radius: 14rpx; }
.status-tag.is-active { background: #E0F0E7; }
.status-tag.is-disabled { background: #F7E0D9; }
.status-text { font-size: 22rpx; font-weight: 500; }
.status-tag.is-active .status-text { color: #2E7D5B; }
.status-tag.is-disabled .status-text { color: #9C4E3F; }
</style>
