<template>
  <view class="page">
    <view class="head">
      <text class="h1">我的作业</text>
      <text class="p">查看作业、提交结果与学情反馈</text>
    </view>
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <view v-else-if="rows.length" class="list">
      <view v-for="a in rows" :key="a.id" class="row" @click="openDetail(a.id)">
        <view class="row-icon">📝</view>
        <view class="row-info">
          <text class="title">{{ a.title }}</text>
          <text class="meta">{{ a.subject || '综合' }} · 截止 {{ a.due_at?.slice(0,16) || '-' }}</text>
        </view>
        <text class="arrow">›</text>
      </view>
    </view>
    <EmptyState v-else title="暂无作业" desc="班主任尚未布置作业" icon="📋" />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../../stores/auth'
import { listAssignments } from '../../../api/assignments'
import EmptyState from '../../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const rows = ref([])

function guardRole() {
  if (!auth.isLoggedIn) { uni.showToast({ title: '请先登录', icon: 'none' }); uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'student') { uni.showToast({ title: '当前角色无法访问', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false }
  return true
}
onShow(() => { if (guardRole()) load() })

async function load() {
  loading.value = true
  try { rows.value = await listAssignments() } catch (_) { rows.value = [] } finally { loading.value = false }
}
function openDetail(id) { uni.navigateTo({ url: `/pages/student/assignmentDetail/index?id=${id}` }) }
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 18rpx; }
.h1 { font-size: 32rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 4rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.list { display: flex; flex-direction: column; gap: 12rpx; }
.row {
  display: flex; align-items: center; gap: 16rpx;
  background: #fff; border-radius: 18rpx; padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(107,92,231,0.05);
}
.row-icon { font-size: 32rpx; flex-shrink: 0; }
.row-info { flex: 1; }
.title { font-size: 28rpx; font-weight: 600; color: #1A1636; display: block; }
.meta { font-size: 22rpx; color: #8E8B9E; display: block; margin-top: 4rpx; }
.arrow { font-size: 32rpx; color: #B8B0F6; }
</style>
