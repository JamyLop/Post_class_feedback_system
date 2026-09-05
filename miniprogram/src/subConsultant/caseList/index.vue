<template>
  <view class="page">
    <view class="head">
      <text class="h1">关联学生档案</text>
      <text class="p">查看您负责的学生的一生一案</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view v-if="!cases.length" class="empty-card">
        <text class="empty-icon">📋</text>
        <text class="empty-title">暂无关联学生</text>
        <text class="empty-desc">请联系管理员将您与学生建立关联关系</text>
      </view>

      <view v-else class="case-list">
        <view v-for="c in cases" :key="c.id" class="case-card" @click="openCase(c.id)">
          <view class="case-top">
            <view class="case-info">
              <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
              <text class="case-meta">{{ c.class_name }} · 第{{ c.version }}版</text>
            </view>
            <CaseStatusTag :status="c.status" />
          </view>
          <text class="case-time">更新于 {{ (c.updated_at || '').slice(0, 10) }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'

const auth = useAuthStore()
const loading = ref(false)
const cases = ref([])

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'consultant') {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function refresh() {
  loading.value = true
  try {
    const list = await listStudentCases().catch(() => [])
    cases.value = Array.isArray(list) ? list : []
  } finally { loading.value = false }
}

function openCase(id) {
  uni.navigateTo({ url: `/subConsultant/caseDetail/index?id=${id}` })
}

onShow(() => { if (guardRole()) refresh() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.empty-card {
  background: #fff; border-radius: 16rpx; padding: 64rpx 28rpx;
  display: flex; flex-direction: column; align-items: center; gap: 12rpx;
  border: 1rpx solid #E0E7E5;
}
.empty-icon { font-size: 48rpx; }
.empty-title { font-size: 28rpx; font-weight: 600; color: #1A1636; }
.empty-desc { font-size: 24rpx; color: #8E8B9E; }

.case-list { display: flex; flex-direction: column; gap: 14rpx; }
.case-card {
  background: #fff; border-radius: 14rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.case-top { display: flex; justify-content: space-between; align-items: center; }
.case-info { flex: 1; }
.case-name { font-size: 28rpx; font-weight: 600; color: #1A1636; display: block; }
.case-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
.case-time { font-size: 22rpx; color: #B0ADB8; display: block; margin-top: 10rpx; }
</style>
