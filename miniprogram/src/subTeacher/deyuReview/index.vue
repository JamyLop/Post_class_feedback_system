<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">德育审查</text>
      <text class="p">班主任提交的方案在此排队，通过后进入执行</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view v-if="pendingCases.length" class="card">
        <text class="card-title">待审查（{{ pendingCases.length }}）</text>
        <view v-for="(c, idx) in pendingCases" :key="c.id" class="case-row" :class="{ 'has-border': idx > 0 }" @click="openCase(c)">
          <view class="case-info">
            <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
            <text class="case-meta">{{ c.class_name }} · 第{{ c.version }}版 · {{ (c.updated_at||'').slice(0,10) }}</text>
          </view>
          <CaseStatusTag :status="c.status" />
        </view>
      </view>
      <EmptyState v-else title="暂无待审查方案" desc="所有方案已处理完毕" />

      <view v-if="recentDecisions.length" class="card">
        <text class="card-title">最近审查记录</text>
        <view v-for="(r, idx) in recentDecisions" :key="r.id" class="review-row" :class="{ 'has-border': idx > 0 }">
          <view class="review-icon" :class="r.decision === 'approved' ? 'approved' : 'rejected'">
            {{ r.decision === 'approved' ? '✓' : '✗' }}
          </view>
          <view class="review-copy">
            <text class="review-label">{{ r.decision === 'approved' ? '通过' : '退回' }} · {{ r.subject || '全局' }}</text>
            <text class="review-time">{{ (r.reviewed_at||'').slice(0,16).replace('T',' ') }}</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases, getStudentCase } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const pendingCases = ref([])
const recentDecisions = ref([])

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'deyu_director') {
    uni.showToast({ title: '仅德育主任可进行审查', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function load() {
  loading.value = true
  try {
    const list = await listStudentCases({ status: 'pending_confirmation' })
    pendingCases.value = Array.isArray(list) ? list : []
    const all = await listStudentCases()
    const withReviews = (Array.isArray(all) ? all : []).filter(c => c.status !== 'pending_confirmation').slice(0, 5)
    const decisions = []
    for (const c of withReviews) {
      try {
        const detail = await getStudentCase(c.id)
        for (const r of (detail.reviews || [])) {
          if (r.review_level === 'deyu' && r.decision) {
            decisions.push({ ...r, student_name: c.student_name, class_name: c.class_name })
          }
        }
      } catch (_) {}
    }
    recentDecisions.value = decisions.sort((a, b) => new Date(b.reviewed_at) - new Date(a.reviewed_at)).slice(0, 10)
  } catch (_) {
    pendingCases.value = []
  } finally { loading.value = false }
}

function openCase(c) {
  uni.navigateTo({ url: `/subTeacher/deyuReview/detail?id=${c.id}` })
}

onShow(() => { if (guardRole()) load() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.head { margin-bottom: 4rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; line-height: 1.5; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 24rpx;
  box-shadow: none;
}
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-bottom: 14rpx; }

.case-row { display: flex; justify-content: space-between; align-items: center; padding: 16rpx 0; gap: 12rpx; }
.case-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.case-info { flex: 1; }
.case-name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.case-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }

.review-row { display: flex; align-items: center; gap: 14rpx; padding: 14rpx 0; }
.review-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.review-icon {
  width: 44rpx; height: 44rpx; border-radius: 12rpx;
  display: flex; align-items: center; justify-content: center;
  font-size: 24rpx; font-weight: 700; flex-shrink: 0;
}
.review-icon.approved { background: #DCFCE7; color: #286349; }
.review-icon.rejected { background: #FEE2E2; color: #A33E39; }
.review-copy { flex: 1; }
.review-label { font-size: 24rpx; color: var(--mp-ink); }
.review-time { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 2rpx; }
</style>
