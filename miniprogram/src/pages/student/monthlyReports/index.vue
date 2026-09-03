<template>
  <view class="page">
    <view class="head">
      <text class="h1">我的月度评价</text>
      <text class="p">查看老师发布的月度综合评价</text>
      <button class="refresh-btn" @click="reload" :loading="loading">刷新</button>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <EmptyState v-if="!reportList.length" title="暂无月度评价" desc="老师尚未发布评价" icon="📋" />
      <view v-else class="report-list">
        <view v-for="(item, idx) in reportList" :key="item.id" class="report-card" :class="{ 'has-border': idx > 0 }">
          <view class="report-head">
            <text class="report-month">{{ item.month_label }}</text>
            <view class="status-tag is-published">
              <text class="status-text">已发布</text>
            </view>
          </view>
          <text class="report-time">发布于 {{ formatTime(item.published_at) }}</text>
          <view class="report-content">
            <text class="content-text">{{ item.final_content || item.ai_content || '暂无内容' }}</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../../stores/auth'
import { listMonthlyReports } from '../../../api/monthlyReports'
import EmptyState from '../../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const reportList = ref([])

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'student') {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function reload() {
  loading.value = true
  try {
    reportList.value = await listMonthlyReports()
  } catch (e) {
    reportList.value = []
  } finally {
    loading.value = false
  }
}

onShow(() => { if (guardRole()) reload() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.head { display: flex; flex-direction: column; gap: 6rpx; }
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

.report-card {
  background: #fff; border-radius: 16rpx; padding: 24rpx;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
}
.report-card.has-border { margin-top: 16rpx; }
.report-head { display: flex; align-items: center; gap: 12rpx; }
.report-month { font-size: 30rpx; font-weight: 700; color: #1A1636; }
.status-tag {
  padding: 4rpx 12rpx; border-radius: 14rpx;
  font-size: 20rpx; font-weight: 500;
}
.status-tag.is-published { background: #EEEDFD; color: #6B5CE7; }
.status-text { white-space: nowrap; }
.report-time { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 6rpx; }
.report-content { margin-top: 16rpx; }
.content-text { font-size: 26rpx; color: #4A4763; line-height: 1.8; white-space: pre-wrap; }
</style>
