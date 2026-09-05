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
        <view class="state-banner" :class="`is-${detail.status}`">

          <text class="state-desc">{{ stateDesc }}</text>
        </view>
        <view v-if="detail.can_manage" class="actions-bar">
          <view class="action-btn" @click="goEdit"><text>编辑</text></view>
          <view class="action-btn" @click="goTasks"><text>任务</text></view>
          <view class="action-btn" @click="goReview"><text>督查</text></view>
          <view v-if="showSubmit" class="action-btn primary" @click="doTransition('pending_confirmation')">
            <text>提交审查</text>
          </view>
          <view v-if="detail.status==='executing'" class="action-btn" @click="doTransition('pending_review')">
            <text>进入复盘</text>
          </view>
        </view>
        <view v-if="detail.viewer_role === 'subject_teacher'" class="actions-bar">
          <view class="action-btn primary" @click="goSuggestion"><text>学科建议</text></view>
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
          <view v-if="detail.student_profile" class="section section-muted">
            <text class="section-h">学生档案</text>
            <view class="field"><text class="dt">姓名</text><text class="dd">{{ detail.student_profile.student_name || '—' }}</text></view>
            <view class="field"><text class="dt">性别</text><text class="dd">{{ detail.student_profile.gender || '—' }}</text></view>
            <view class="field"><text class="dt">来源学校</text><text class="dd">{{ detail.student_profile.source_school || '—' }}</text></view>
          </view>
        </view>

        <view v-if="active==='subjects'" class="tab-panel">
          <view v-if="!detail.subject_plans.length" class="empty-text">暂无学科方案</view>
          <view v-for="plan in detail.subject_plans" :key="plan.id" class="plan-card">
            <view class="plan-head">
              <text class="subject-chip">{{ plan.subject }}</text>
              <text v-if="detail.can_manage" class="edit-link" @click="goEditPlan(plan.subject)">编辑</text>
            </view>
            <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
            <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
            <view class="field"><text class="dt">奋斗目标</text><text class="dd">{{ plan.struggle_goal || '—' }}</text></view>
            <view class="field"><text class="dt">高考要求</text><text class="dd">{{ plan.gaokao_requirement || '—' }}</text></view>
            <view class="field"><text class="dt">具体强化</text><text class="dd">{{ plan.reinforcement || '—' }}</text></view>
          </view>
          <view v-if="detail.can_manage" class="add-plan">
            <picker :range="availableSubjects" @change="onAddPlan">
              <text class="add-link">+ 新增学科方案</text>
            </picker>
          </view>
        </view>

        <view v-if="active==='tasks'" class="tab-panel">
          <view v-if="detail.can_manage" class="section-head-row">
            <text class="section-h">任务列表</text>
            <text class="add-link" @click="goTasks">管理</text>
          </view>
          <view v-if="!detail.tasks.length" class="empty-text">暂无任务</view>
          <view v-for="task in detail.tasks" :key="task.id" class="task-card" @click="detail.can_manage && goCheckin(task.id)">
            <view class="task-head">
              <text class="subject-tag">{{ task.subject || '综合' }}</text>
              <text class="task-title">{{ task.title }}</text>
            </view>
            <text class="task-meta">{{ task.starts_on }} 至 {{ task.due_on }} · {{ taskStatus(task.status) }}</text>
          </view>
          <view v-if="detail.task_checkins.length" class="checkin-section">
            <text class="section-h">执行记录（最近10条）</text>
            <Timeline :items="checkinItems" />
          </view>
        </view>

        <view v-if="active==='reviews'" class="tab-panel">
          <view v-if="detail.can_manage" class="section-head-row">
            <text class="section-h">督查记录</text>
            <text class="add-link" @click="goReview">提交督查</text>
          </view>
          <view v-if="!detail.reviews.length" class="empty-text">暂无督查复盘</view>
          <Timeline v-else :items="reviewItems" />
        </view>
      </view>
    </template>
    <EmptyState v-else title="档案不存在" desc="可能已被移除或无权查看" />
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, transitionCase } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import Timeline from '../../components/Timeline.vue'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)
const active = ref('overview')
const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'subjects', label: '学科' },
  { key: 'tasks', label: '任务' },
  { key: 'reviews', label: '督查' },
]

const statusCopy = {
  draft: ['草稿', '等待教师完善'],
  pending_confirmation: ['待审查', '班主任已提交，审查中'],
  revision_required: ['待整改', '已退回，等待整改'],
  executing: ['执行中', '家长可见当前版本'],
  pending_review: ['待复盘', '已进入阶段复盘'],
  adjusted: ['已调整', '已生成新版本'],
  archived: ['已归档', '只读归档'],
}
const stateTitle = computed(() => statusCopy[detail.value?.status]?.[0] || detail.value?.status)
const stateDesc = computed(() => statusCopy[detail.value?.status]?.[1] || '')
const showSubmit = computed(() => ['draft', 'revision_required', 'adjusted'].includes(detail.value?.status))

const allSubjects = ['语文','数学','英语','物理','化学','生物','政治','历史','地理']
const availableSubjects = computed(() => {
  const used = new Set((detail.value?.subject_plans || []).map(p => p.subject))
  return allSubjects.filter(s => !used.has(s))
})

const checkinItems = computed(() => (detail.value?.task_checkins || []).slice(0, 10).map(c => ({
  title: `${c.completion_rate}% · ${taskTitle(c.task_id)}`,
  desc: c.self_check || '—',
  time: c.checked_in_at?.slice(0, 16).replace('T', ' '),
})))
const reviewItems = computed(() => (detail.value?.reviews || []).map(r => ({
  title: `${levelLabel(r.review_level)}${r.subject ? ' · '+r.subject : ''}`,
  desc: `${r.problem || ''}${r.corrective_action ? '｜整改：'+r.corrective_action : ''}${r.recheck_result ? '｜复查：'+r.recheck_result : ''}`,
  time: r.reviewed_at?.slice(0,16).replace('T',' '),
})))

function taskStatus(v) { return { pending:'待执行', in_progress:'执行中', completed:'已完成', cancelled:'已取消' }[v] || v }
function levelLabel(v) { return { school:'校级督查', principal:'校长督察', deyu:'德育督查', head_teacher:'班主任督查', subject:'学科督查' }[v] || v }
function taskTitle(id) { return detail.value?.tasks.find(t => t.id === id)?.title || '任务' }

function caseId() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options?.id || cur.$page?.options?.id
}

async function load() {
  loading.value = true
  try {
    const id = caseId()
    if (!id) throw new Error('缺少 case id')
    detail.value = await getStudentCase(id)
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loading.value = false }
}

async function doTransition(target) {
  uni.showModal({
    title: target === 'pending_confirmation' ? '提交审查' : '进入复盘',
    content: target === 'pending_confirmation' ? '提交后进入审查流程' : '确认进入阶段复盘？',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await transitionCase(caseId(), { target_status: target, reason: '' })
        uni.showToast({ title: '操作成功', icon: 'success' })
        load()
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    }
  })
}

function goEdit() { uni.navigateTo({ url: `/subTeacher/caseEdit/index?caseId=${caseId()}` }) }
function goTasks() { uni.navigateTo({ url: `/subTeacher/taskManager/index?caseId=${caseId()}` }) }
function goCheckin(taskId) { uni.navigateTo({ url: `/subTeacher/checkin/index?caseId=${caseId()}&taskId=${taskId}` }) }
function goReview() { uni.navigateTo({ url: `/subTeacher/reviewCreate/index?caseId=${caseId()}` }) }
function goEditPlan(subject) { uni.navigateTo({ url: `/subTeacher/caseEdit/index?caseId=${caseId()}&tab=subjects&subject=${encodeURIComponent(subject)}` }) }
function goSuggestion() { uni.navigateTo({ url: `/subTeacher/subjectSuggestion/index?id=${caseId()}` }) }
function onAddPlan(e) {
  const subject = availableSubjects.value[e.detail.value]
  if (subject) goEditPlan(subject)
}

onShow(() => load())

</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.header-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  box-shadow: none;
}
.title-row { display: flex; gap: 12rpx; align-items: center; }
.h1 { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 8rpx; }
.state-banner { margin-top: 14rpx; padding: 16rpx 18rpx; border-radius: 14rpx; background: #F3F5F8; }
.state-banner.is-executing { background: #EEF8EE; }
.state-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.state-desc { font-size: 24rpx; color: #526177; display: block; margin-top: 4rpx; }

.actions-bar { display: flex; flex-wrap: wrap; gap: 12rpx; margin-top: 18rpx; }
.action-btn {
  display: flex; align-items: center; gap: 6rpx;
  font-size: 24rpx; padding: 12rpx 20rpx;
  border-radius: 12rpx;
  background: #F3F5F8;
  color: var(--mp-body);
}
.action-btn.primary { background: var(--mp-primary); color: #fff; }
.action-icon { font-size: 24rpx; }

.tabs {
  background: #fff;
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: none;
}
.tab-bar { display: flex; border-bottom: 2rpx solid var(--mp-soft); }
.tab {
  flex: 1; text-align: center; padding: 22rpx 0;
  font-size: 26rpx; color: var(--mp-muted);
  border-bottom: 4rpx solid transparent;
}
.tab.active { color: var(--mp-primary); border-bottom-color: var(--mp-primary); font-weight: 600; }
.tab-panel { padding: 24rpx; display: flex; flex-direction: column; gap: 18rpx; }

.section { display: flex; flex-direction: column; gap: 8rpx; }
.section-muted { background: #F7F8FA; border-radius: 14rpx; padding: 18rpx; }
.section-h { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.section-body { font-size: 26rpx; color: var(--mp-body); line-height: 1.7; white-space: pre-wrap; }
.section-head-row { display: flex; justify-content: space-between; align-items: center; }
.empty-text { text-align: center; color: var(--mp-muted); padding: 28rpx; font-size: 24rpx; }

.field { display: flex; flex-direction: column; gap: 4rpx; margin-top: 8rpx; }
.dt { font-size: 24rpx; color: var(--mp-muted); }
.dd { font-size: 24rpx; color: var(--mp-body); line-height: 1.6; white-space: pre-wrap; }

.plan-card {
  background: #F7F8FA;
  border-radius: 14rpx;
  padding: 20rpx;
  display: flex; flex-direction: column; gap: 10rpx;
}
.plan-head { display: flex; justify-content: space-between; align-items: center; }
.subject-chip {
  font-size: 24rpx; font-weight: 600;
  color: var(--mp-primary);
  background: var(--mp-soft);
  padding: 6rpx 16rpx;
  border-radius: 16rpx;
}
.edit-link { font-size: 24rpx; color: var(--mp-primary); }
.add-plan { text-align: center; padding: 14rpx; }
.add-link { font-size: 24rpx; color: var(--mp-primary); font-weight: 500; }

.task-card {
  background: #F7F8FA;
  border-radius: 14rpx;
  padding: 18rpx;
}
.task-head { display: flex; gap: 10rpx; align-items: center; flex-wrap: wrap; }
.subject-tag {
  font-size: 24rpx; color: var(--mp-primary);
  background: var(--mp-soft);
  padding: 4rpx 12rpx;
  border-radius: 16rpx;
}
.task-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.task-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.checkin-section { margin-top: 12rpx; }
</style>

<style scoped src="../../styles/details.css"></style>
