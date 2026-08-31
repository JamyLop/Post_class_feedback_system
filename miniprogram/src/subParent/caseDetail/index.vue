<template>
  <view class="page">
    <view v-if="loading" class="skeleton">加载中…</view>
    <template v-else-if="detail">
      <view class="header">
        <view class="title-row">
          <text class="h1">{{ detail.student_name || `学生 #${detail.student_id}` }}</text>
          <text class="suffix">学业发展总案</text>
        </view>
        <view class="meta">
          <CaseStatusTag :status="detail.status" />
          <text>{{ detail.class_name }}</text>
          <text>第{{ detail.version }}版</text>
        </view>
        <view class="state-banner" :class="`is-${detail.status}`">
          <text class="state-title">{{ stateTitle }}</text>
          <text class="state-desc">{{ stateDesc }}</text>
        </view>
      </view>

      <view class="tabs">
        <view class="tab-bar">
          <text v-for="t in tabs" :key="t.key" class="tab" :class="{ active: active===t.key }" @click="active=t.key">{{ t.label }}</text>
        </view>

        <view v-if="active==='overview'" class="tab-panel">
          <view class="section">
            <text class="section-h">总体问题</text>
            <text class="section-body">{{ detail.overall_problem || '尚未填写' }}</text>
          </view>
          <view class="section">
            <text class="section-h">升学目标</text>
            <text class="section-body">{{ detail.admission_target || '尚未填写' }}</text>
          </view>
          <view class="section muted">
            <text class="section-h">当前状态说明</text>
            <text class="section-body">{{ detail.current_summary || '—' }}</text>
          </view>
        </view>

        <view v-if="active==='subjects'" class="tab-panel">
          <view v-if="!detail.subject_plans.length" class="empty">暂无学科方案</view>
          <view v-for="plan in detail.subject_plans" :key="plan.id" class="plan-card">
            <view class="plan-head">
              <text class="subject-chip">{{ plan.subject }}</text>
              <text class="teacher-tip">负责教师 #{{ plan.teacher_id }}</text>
            </view>
            <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
            <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
            <view class="field"><text class="dt">奋斗目标</text><text class="dd">{{ plan.struggle_goal || '—' }}</text></view>
            <view class="field"><text class="dt">高考要求</text><text class="dd">{{ plan.gaokao_requirement || '—' }}</text></view>
            <view class="field"><text class="dt">具体强化</text><text class="dd">{{ plan.reinforcement || '—' }}</text></view>
          </view>
        </view>

        <view v-if="active==='tasks'" class="tab-panel">
          <view v-if="!detail.tasks.length" class="empty">暂无任务</view>
          <view v-for="task in detail.tasks" :key="task.id" class="task-card">
            <view class="task-head">
              <text class="subject-tag">{{ task.subject || '综合' }}</text>
              <text class="task-title">{{ task.title }}</text>
              <text class="cadence">{{ cadenceLabel(task.cadence) }}</text>
            </view>
            <text class="task-desc">{{ task.description }}</text>
            <text class="task-meta">{{ task.starts_on }} 至 {{ task.due_on }} · {{ task.status }}</text>
          </view>
          <view v-if="detail.task_checkins.length" class="checkin-section">
            <text class="section-h">执行记录</text>
            <Timeline :items="checkinItems" />
          </view>
        </view>

        <view v-if="active==='reviews'" class="tab-panel">
          <view v-if="!detail.reviews.length" class="empty">暂无督查复盘</view>
          <Timeline v-else :items="reviewItems" />
        </view>
      </view>
    </template>
    <EmptyState v-else title="档案不存在" desc="可能已被移除或无权查看" />
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStudentCase } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import Timeline from '../../components/Timeline.vue'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)
const active = ref('overview')
const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'subjects', label: '学科方案' },
  { key: 'tasks', label: '任务执行' },
  { key: 'reviews', label: '督查复盘' },
]

const statusCopy = {
  draft: ['草稿', '等待教师完善'],
  pending_confirmation: ['待德育审查', '班主任已提交，德育主任审查中'],
  revision_required: ['待整改', '德育已退回，等待班主任整改'],
  executing: ['执行中', '家长可见当前版本'],
  pending_review: ['待复盘', '已进入阶段复盘'],
  adjusted: ['已调整', '已生成新版本'],
  archived: ['已归档', '只读归档'],
}
const stateTitle = computed(() => statusCopy[detail.value?.status]?.[0] || detail.value?.status)
const stateDesc = computed(() => statusCopy[detail.value?.status]?.[1] || '')

const checkinItems = computed(() => (detail.value?.task_checkins || []).slice(0, 20).map((c) => ({
  title: `${c.completion_rate}% · ${taskTitle(c.task_id)}`,
  desc: c.self_check || '—',
  time: c.checked_in_at?.slice(0, 16).replace('T', ' '),
})))
const reviewItems = computed(() => (detail.value?.reviews || []).map((r) => ({
  title: `${levelLabel(r.review_level)}${r.subject ? ' · '+r.subject : ''}`,
  desc: `${r.problem || ''}${r.corrective_action ? '｜整改：'+r.corrective_action : ''}${r.recheck_result ? '｜复查：'+r.recheck_result : ''}`,
  time: r.reviewed_at?.slice(0,16).replace('T',' '),
})))

function cadenceLabel(v) { return { daily:'日计划', weekly:'周计划', monthly:'月计划'}[v] || v }
function levelLabel(v) { return { school:'校级督查', principal:'校长督察', deyu:'德育督查', head_teacher:'班主任督查', subject:'学科督查'}[v] || v }
function taskTitle(id) { return detail.value?.tasks.find((t)=>t.id===id)?.title || '任务' }

async function load() {
  loading.value = true
  try {
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1]
    const id = cur.options?.id || cur.$page?.options?.id
    if (!id) throw new Error('缺少 case id')
    detail.value = await getStudentCase(id)
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding:24rpx 20rpx 48rpx; display:flex; flex-direction:column; gap:20rpx; }
.skeleton { text-align:center; padding:48rpx; color:#64748b; }
.header { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:28rpx; }
.title-row { display:flex; gap:12rpx; align-items:baseline; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.suffix { font-size:22rpx; color:#64748b; }
.meta { display:flex; gap:12rpx; align-items:center; flex-wrap:wrap; margin-top:12rpx; font-size:22rpx; color:#64748b; }
.state-banner { margin-top:16rpx; padding:16rpx; border-radius:12rpx; background:#f8fafc; border:1rpx solid #e2e8f0; }
.state-banner.is-executing { background:#eff6ff; border-color:#bfdbfe; }
.state-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; }
.state-desc { font-size:22rpx; color:#475569; display:block; margin-top:4rpx; }
.tabs { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; overflow:hidden; }
.tab-bar { display:flex; border-bottom:1rpx solid #e2e8f0; }
.tab { flex:1; text-align:center; padding:22rpx 0; font-size:26rpx; color:#64748b; border-bottom:3rpx solid transparent; }
.tab.active { color:#2563eb; border-bottom-color:#2563eb; font-weight:600; background:#f8fafc; }
.tab-panel { padding:24rpx; display:flex; flex-direction:column; gap:20rpx; }
.section { display:flex; flex-direction:column; gap:8rpx; }
.section.muted { background:#f8fafc; border:1rpx solid #f1f5f9; border-radius:12rpx; padding:16rpx; }
.section-h { font-size:24rpx; font-weight:600; color:#0f172a; }
.section-body { font-size:26rpx; color:#334155; line-height:1.7; white-space:pre-wrap; }
.empty { text-align:center; color:#94a3b8; padding:24rpx; font-size:24rpx; }
.plan-card { border:1rpx solid #e2e8f0; border-radius:12rpx; padding:20rpx; display:flex; flex-direction:column; gap:12rpx; }
.plan-head { display:flex; justify-content:space-between; align-items:center; }
.subject-chip { font-size:22rpx; font-weight:600; color:#2563eb; background:#eff6ff; border:1rpx solid #bfdbfe; padding:4rpx 12rpx; border-radius:999rpx; }
.teacher-tip { font-size:20rpx; color:#94a3b8; }
.field { display:flex; flex-direction:column; gap:4rpx; }
.dt { font-size:22rpx; color:#64748b; }
.dd { font-size:24rpx; color:#334155; line-height:1.6; white-space:pre-wrap; }
.task-card { border:1rpx solid #e2e8f0; border-radius:12rpx; padding:20rpx; }
.task-head { display:flex; gap:12rpx; align-items:center; flex-wrap:wrap; }
.subject-tag { font-size:20rpx; color:#2563eb; background:#eff6ff; border:1rpx solid #bfdbfe; padding:4rpx 10rpx; border-radius:999rpx; }
.task-title { font-size:26rpx; font-weight:600; color:#0f172a; }
.cadence { font-size:20rpx; color:#64748b; background:#f1f5f9; padding:4rpx 10rpx; border-radius:999rpx; }
.task-desc { font-size:24rpx; color:#475569; display:block; margin-top:8rpx; line-height:1.5; }
.task-meta { font-size:22rpx; color:#94a3b8; display:block; margin-top:6rpx; }
.checkin-section { margin-top:12rpx; }
</style>
