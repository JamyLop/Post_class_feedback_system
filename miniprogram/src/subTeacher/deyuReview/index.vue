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
      <view class="card change-req-card">
        <text class="card-title">周任务修改申请（{{ changeRequests.length }}）</text>
        <view v-if="changeRequests.length">
          <view v-for="(r, idx) in changeRequests" :key="r.id" class="case-row" :class="{ 'has-border': idx > 0 }">
            <view class="case-info">
              <text class="case-name">{{ r.task_title }}</text>
              <text class="case-meta">{{ r.student_name || `学生#${r.student_id}` }} · {{ r.class_name || '' }} · {{ r.subject }} · 每周任务</text>
              <text class="case-meta">原因：{{ r.reason }}</text>
            </view>
            <view class="req-actions">
              <view class="req-btn reject" @click.stop="handleDecide(r, 'rejected')"><text>驳回</text></view>
              <view class="req-btn approve" @click.stop="handleDecide(r, 'approved')"><text>同意</text></view>
            </view>
          </view>
        </view>
        <view v-else class="empty-text">暂无待审批的修改申请，有班主任提交后会在此出现</view>
      </view>

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
import { listStudentCases, getStudentCase, listTaskChangeRequests, decideTaskChange } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const pendingCases = ref([])
const recentDecisions = ref([])
const changeRequests = ref([])

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
    try { changeRequests.value = await listTaskChangeRequests() } catch (_) { changeRequests.value = [] }
  } catch (_) {
    pendingCases.value = []
  } finally { loading.value = false }
}

async function handleDecide(row, decision) {
  const title = decision === 'approved' ? '同意并退回整改' : '驳回申请'
  const content = decision === 'approved' ? '同意后档案将退回整改，班主任可修改该任务' : '确认驳回该修改申请？'
  uni.showModal({
    title, content,
    success: async (res) => {
      if (!res.confirm) return
      try {
        await decideTaskChange(row.id, { decision })
        uni.showToast({ title: decision === 'approved' ? '已同意并退回整改' : '已驳回', icon: 'success' })
        load()
      } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
    }
  })
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
.change-req-card { border: 2rpx solid #FCD34D; }
.empty-text { text-align: center; color: var(--mp-muted); padding: 18rpx; font-size: 24rpx; }
.req-actions { display: flex; gap: 12rpx; flex-shrink: 0; }
.req-btn { padding: 10rpx 18rpx; border-radius: 10rpx; font-size: 24rpx; }
.req-btn.approve { background: #286349; color: #fff; }
.req-btn.reject { background: #fff; color: #A33E39; border: 1rpx solid #FECACA; }
</style>
