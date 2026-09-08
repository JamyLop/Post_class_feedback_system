<template>
  <view class="page">
    <WorkspaceLink />
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="detail">
      <view class="header-card">
        <view class="title-row">
          <text class="h1">{{ detail.student_name || `学生 #${detail.student_id}` }}</text>
          <CaseStatusTag :status="detail.status" />
        </view>
        <text class="meta">{{ detail.class_name }} · 第{{ detail.version }}版</text>
      </view>

      <view class="card">
        <view class="section">
          <text class="section-h">总体问题</text>
          <text class="section-body">{{ detail.overall_problem || '尚未填写' }}</text>
        </view>
        <view class="divider"></view>
        <view class="section">
          <text class="section-h">升学目标</text>
          <text class="section-body">{{ detail.admission_target || '尚未填写' }}</text>
        </view>
      </view>

      <view v-if="detail.subject_plans.length" class="card">
        <text class="section-h">学科方案（{{ detail.subject_plans.length }}）</text>
        <view v-for="(plan, idx) in detail.subject_plans" :key="plan.id" class="plan-row" :class="{ 'has-border': idx > 0 }">
          <text class="plan-chip">{{ plan.subject }}</text>
          <text class="plan-desc">{{ (plan.problem_location || '').slice(0, 40) || '暂无' }}</text>
        </view>
      </view>

      <view class="card change-req-card">
        <text class="section-h">周任务修改申请（{{ changeRequests.length }}）</text>
        <view v-if="changeRequests.length">
          <view v-for="(r, idx) in changeRequests" :key="r.id" class="change-req-row" :class="{ 'has-border': idx > 0 }">
            <text class="req-title">{{ r.task_title }} · {{ r.subject }} · 每周任务</text>
            <text class="req-reason">原因：{{ r.reason }}</text>
            <text class="req-meta">{{ r.student_name || '' }} · {{ r.class_name || '' }} · {{ (r.reviewed_at||'').slice(0,16).replace('T',' ') }}</text>
            <view class="req-actions">
              <view class="req-btn reject" @click="decide(r, 'rejected')"><text>驳回</text></view>
              <view class="req-btn approve" @click="decide(r, 'approved')"><text>同意并退回整改</text></view>
            </view>
          </view>
        </view>
        <view v-else class="empty-text">该档案暂无待审批的修改申请</view>
      </view>

      <view class="card action-card">
        <text class="action-title">审查决定</text>
        <view class="decision-row">
          <view class="decision-btn approved" :class="{ active: decision === 'approved' }" @click="decision='approved'">
            <text class="decision-icon">✓</text>
            <text class="decision-label">通过</text>
            <text class="decision-desc">方案进入执行</text>
          </view>
          <view class="decision-btn rejected" :class="{ active: decision === 'changes_requested' }" @click="decision='changes_requested'">
            <text class="decision-icon">✗</text>
            <text class="decision-label">退回修改</text>
            <text class="decision-desc">生成整改待办</text>
          </view>
        </view>

        <template v-if="decision === 'changes_requested'">
          <view class="field">
            <text class="label">问题描述 *</text>
            <textarea v-model="form.problem" class="textarea" placeholder="方案存在的问题" />
          </view>
          <view class="field">
            <text class="label">修改要求 *</text>
            <textarea v-model="form.corrective_action" class="textarea" placeholder="具体修改要求" />
          </view>
          <view class="field">
            <text class="label">整改截止日期 *</text>
            <picker mode="date" @change="e => form.correction_due_on = e.detail.value">
              <view class="picker">{{ form.correction_due_on || '选择截止日期' }}</view>
            </picker>
          </view>
        </template>

        <button
          class="btn-submit"
          :class="decision === 'approved' ? 'btn-approve' : 'btn-reject'"
          :loading="submitting" :disabled="submitting"
          @click="submit"
        >
          {{ decision === 'approved' ? '确认通过' : '确认退回' }}
        </button>
      </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, reactive, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, deyuReview, listTaskChangeRequests, decideTaskChange } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'

const loading = ref(false)
const submitting = ref(false)
const detail = ref(null)
const decision = ref('approved')
const form = reactive({ problem: '', corrective_action: '', correction_due_on: '' })
const changeRequests = ref([])

function getCaseId() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options?.id || cur.$page?.options?.id
}

async function load() {
  loading.value = true
  try {
    detail.value = await getStudentCase(getCaseId())
    try {
      const list = await listTaskChangeRequests()
      changeRequests.value = (Array.isArray(list) ? list : []).filter(r => String(r.case_id) === String(getCaseId()))
    } catch (_) { changeRequests.value = [] }
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loading.value = false }
}

async function decide(row, decisionVal) {
  const title = decisionVal === 'approved' ? '同意并退回整改' : '驳回申请'
  uni.showModal({
    title, content: decisionVal === 'approved' ? '同意后档案将退回整改，班主任可修改该任务' : '确认驳回？',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await decideTaskChange(row.id, { decision: decisionVal })
        uni.showToast({ title: decisionVal === 'approved' ? '已同意并退回整改' : '已驳回', icon: 'success' })
        load()
      } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
    }
  })
}

async function submit() {
  if (decision.value === 'changes_requested') {
    if (!form.problem || !form.corrective_action || !form.correction_due_on) {
      return uni.showToast({ title: '退回时需填写完整信息', icon: 'none' })
    }
  }
  uni.showModal({
    title: decision.value === 'approved' ? '确认通过' : '确认退回',
    content: decision.value === 'approved' ? '通过后档案进入执行状态' : '退回后班主任将收到整改待办',
    success: async (res) => {
      if (!res.confirm) return
      submitting.value = true
      try {
        await deyuReview(getCaseId(), {
          decision: decision.value,
          problem: form.problem,
          corrective_action: form.corrective_action,
          correction_due_on: form.correction_due_on || null,
        })
        uni.showToast({ title: decision.value === 'approved' ? '已通过' : '已退回', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 1500)
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      } finally { submitting.value = false }
    }
  })
}

onShow(() => load())

</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.header-card {
  background: #fff; border-radius: 20rpx; padding: 28rpx;
  box-shadow: none;
}
.title-row { display: flex; gap: 12rpx; align-items: center; }
.h1 { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 8rpx; }

.card {
  background: #fff; border-radius: 20rpx; padding: 24rpx;
  box-shadow: none;
  display: flex; flex-direction: column; gap: 14rpx;
}
.divider { height: 2rpx; background: var(--mp-soft); margin: 4rpx 0; }
.section { display: flex; flex-direction: column; gap: 8rpx; }
.section-h { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.section-body { font-size: 26rpx; color: var(--mp-body); line-height: 1.7; white-space: pre-wrap; }

.plan-row { display: flex; gap: 12rpx; align-items: center; padding: 10rpx 0; }
.plan-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.plan-chip {
  font-size: 24rpx; font-weight: 600; color: var(--mp-primary);
  background: var(--mp-soft); padding: 6rpx 16rpx; border-radius: 16rpx;
}
.plan-desc { font-size: 24rpx; color: var(--mp-muted); }

.action-card { gap: 16rpx; }
.action-title { font-size: 28rpx; font-weight: 700; color: var(--mp-ink); }
.decision-row { display: flex; gap: 14rpx; }
.decision-btn {
  flex: 1; border: 2rpx solid var(--mp-line);
  border-radius: 16rpx; padding: 20rpx; text-align: center;
}
.decision-btn.active.approved { border-color: #286349; background: #F0FDF4; }
.decision-btn.active.rejected { border-color: #A33E39; background: #FEF2F2; }
.decision-icon { font-size: 36rpx; display: block; }
.decision-label { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-top: 4rpx; }
.decision-desc { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }

.field { display: flex; flex-direction: column; gap: 6rpx; }
.label { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.textarea {
  border: 2rpx solid var(--mp-line); border-radius: 14rpx;
  padding: 18rpx 20rpx; font-size: 26rpx; min-height: 120rpx; background: #fff;
}
.picker {
  border: 2rpx solid var(--mp-line); border-radius: 14rpx;
  padding: 18rpx 20rpx; background: #fff; font-size: 26rpx; color: var(--mp-ink);
}

.btn-submit { border-radius: 14rpx; padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none; }
.btn-submit::after { border: none; }
.btn-approve { background: #286349; color: #fff; }
.btn-reject { background: #A33E39; color: #fff; }
.change-req-card { border: 2rpx solid #FCD34D; }
.change-req-row { padding: 14rpx 0; display: flex; flex-direction: column; gap: 6rpx; }
.change-req-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.req-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.req-reason { font-size: 24rpx; color: var(--mp-body); }
.req-meta { font-size: 22rpx; color: var(--mp-muted); }
.req-actions { display: flex; gap: 12rpx; margin-top: 6rpx; }
.req-btn { padding: 10rpx 18rpx; border-radius: 10rpx; font-size: 24rpx; }
.req-btn.approve { background: #286349; color: #fff; }
.req-btn.reject { background: #fff; color: #A33E39; border: 1rpx solid #FECACA; }
</style>
