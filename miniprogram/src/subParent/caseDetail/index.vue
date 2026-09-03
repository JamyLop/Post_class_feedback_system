<template>
  <view class="page">
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="detail">
      <view class="header-card">
        <view class="title-row">
          <text class="h1">{{ detail.student_name || `学生 #${detail.student_id}` }}</text>
          <text class="suffix">学业发展总案</text>
        </view>
        <view class="meta">
          <CaseStatusTag :status="detail.status" />
          <text class="meta-text">{{ detail.class_name }} · 第{{ detail.version }}版</text>
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
          <view class="section section-muted">
            <text class="section-h">当前状态说明</text>
            <text class="section-body">{{ detail.current_summary || '—' }}</text>
          </view>
        </view>

        <view v-if="active==='subjects'" class="tab-panel">
          <EmptyState v-if="!detail.subject_plans.length" title="暂无学科方案" icon="📖" />
          <view v-for="plan in detail.subject_plans" :key="plan.id" class="plan-card">
            <view class="plan-head">
              <text class="subject-chip">{{ plan.subject }}</text>
              <text class="teacher-tip">教师 #{{ plan.teacher_id }}</text>
            </view>
            <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
            <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
            <view class="field"><text class="dt">奋斗目标</text><text class="dd">{{ plan.struggle_goal || '—' }}</text></view>
            <view class="field"><text class="dt">高考要求</text><text class="dd">{{ plan.gaokao_requirement || '—' }}</text></view>
            <view class="field"><text class="dt">具体强化</text><text class="dd">{{ plan.reinforcement || '—' }}</text></view>
          </view>
        </view>

        <view v-if="active==='tasks'" class="tab-panel">
          <EmptyState v-if="!detail.tasks.length" title="暂无任务" icon="📋" />
          <view v-for="task in detail.tasks" :key="task.id" class="task-card" @click="openTask(task.id)">
            <view class="task-head">
              <text class="subject-tag">{{ task.subject || '综合' }}</text>
              <text class="task-title">{{ task.title }}</text>
            </view>
            <text class="task-meta">{{ task.starts_on }} 至 {{ task.due_on }} · {{ task.status }}</text>
            <text class="task-link">查看时间轴与打卡</text>
          </view>
          <view v-if="detail.task_checkins.length" class="checkin-section">
            <text class="section-h">执行记录</text>
            <Timeline :items="checkinItems" />
          </view>
        </view>

        <view v-if="active==='reviews'" class="tab-panel">
          <EmptyState v-if="!detail.reviews.length" title="暂无督查复盘" icon="📋" />
          <Timeline v-else :items="reviewItems" />
        </view>
      </view>
    </template>
    <EmptyState v-else title="档案不存在" desc="可能已被移除或无权查看" icon="📄" />
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
  pending_confirmation: ['待审查', '已提交审查中'],
  revision_required: ['待整改', '已退回，等待整改'],
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

function levelLabel(v) { return { school:'校级督查', principal:'校长督察', deyu:'德育督查', head_teacher:'班主任督查', subject:'学科督查'}[v] || v }
function taskTitle(id) { return detail.value?.tasks.find((t)=>t.id===id)?.title || '任务' }
function openTask(taskId) {
  if (!detail.value) return
  uni.navigateTo({ url: `/subParent/taskDetail/index?caseId=${detail.value.id}&taskId=${taskId}` })
}

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
  } finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.header-card {
  background: #fff; border-radius: 20rpx; padding: 28rpx;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
}
.title-row { display: flex; gap: 12rpx; align-items: baseline; }
.h1 { font-size: 32rpx; font-weight: 700; color: #1A1636; }
.suffix { font-size: 22rpx; color: #8E8B9E; }
.meta { display: flex; gap: 12rpx; align-items: center; flex-wrap: wrap; margin-top: 10rpx; }
.meta-text { font-size: 22rpx; color: #8E8B9E; }
.state-banner { margin-top: 14rpx; padding: 16rpx 18rpx; border-radius: 12rpx; background: #FAF9F7; }
.state-banner.is-executing { background: #F0FDF4; }
.state-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.state-desc { font-size: 22rpx; color: #6E6B83; display: block; margin-top: 4rpx; }

.tabs {
  background: #fff; border-radius: 20rpx; overflow: hidden;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
}
.tab-bar { display: flex; border-bottom: 2rpx solid #F0EFFC; }
.tab {
  flex: 1; text-align: center; padding: 22rpx 0;
  font-size: 26rpx; color: #8E8B9E;
  border-bottom: 4rpx solid transparent;
}
.tab.active { color: #6B5CE7; border-bottom-color: #6B5CE7; font-weight: 600; background: #FAF9F7; }
.tab-panel { padding: 24rpx; display: flex; flex-direction: column; gap: 18rpx; }

.section { display: flex; flex-direction: column; gap: 8rpx; }
.section-muted { background: #FAF9F7; border-radius: 12rpx; padding: 16rpx; }
.section-h { font-size: 24rpx; font-weight: 600; color: #1A1636; }
.section-body { font-size: 26rpx; color: #4A4763; line-height: 1.7; white-space: pre-wrap; }

.plan-card {
  background: #FAF9F7; border-radius: 14rpx; padding: 20rpx;
  display: flex; flex-direction: column; gap: 10rpx;
}
.plan-head { display: flex; justify-content: space-between; align-items: center; }
.subject-chip {
  font-size: 22rpx; font-weight: 600; color: #6B5CE7;
  background: #EEEDFD; padding: 6rpx 16rpx; border-radius: 16rpx;
}
.teacher-tip { font-size: 20rpx; color: #A09CB5; }
.field { display: flex; flex-direction: column; gap: 4rpx; margin-top: 4rpx; }
.dt { font-size: 22rpx; color: #8E8B9E; }
.dd { font-size: 24rpx; color: #4A4763; line-height: 1.6; white-space: pre-wrap; }

.task-card {
  background: #FAF9F7; border-radius: 14rpx; padding: 20rpx;
}
.task-head { display: flex; gap: 12rpx; align-items: center; flex-wrap: wrap; }
.subject-tag {
  font-size: 20rpx; color: #6B5CE7; background: #EEEDFD;
  padding: 4rpx 12rpx; border-radius: 16rpx;
}
.task-title { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.task-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 6rpx; }
.task-link { font-size: 22rpx; color: #6B5CE7; display: block; margin-top: 8rpx; }
.checkin-section { margin-top: 12rpx; }
</style>
