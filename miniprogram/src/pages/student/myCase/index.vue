<template>
  <view class="page">
    <view class="head">
      <text class="h1">我的档案</text>
      <text class="p">只读查看已发布的一生一案</text>
      <button class="refresh-btn" @click="reload" :loading="loading">刷新</button>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="detail">
      <view class="header-card">
        <view class="title-row">
          <text class="name">{{ detail.student_name || `学生 #${detail.student_id}` }}</text>
          <CaseStatusTag :status="detail.status" />
        </view>
        <text class="meta">{{ detail.class_name || '' }} · 第{{ detail.version }}版</text>
        <view class="state-banner" :class="`is-${detail.status}`">
          <text class="state-title">{{ stateTitle }}</text>
          <text class="state-desc">{{ stateDesc }}</text>
        </view>
      </view>

      <view class="tabs">
        <text v-for="t in tabs" :key="t.key" class="tab" :class="{ active: active===t.key }" @click="active=t.key">{{ t.label }}</text>
      </view>

      <view v-if="active==='overview'" class="panel">
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

      <view v-if="active==='subjects'" class="panel">
        <EmptyState v-if="!detail.subject_plans.length" title="暂无学科方案" icon="📖" />
        <view v-for="plan in detail.subject_plans" :key="plan.id" class="plan-card">
          <text class="subject-chip">{{ plan.subject }}</text>
          <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
          <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
          <view class="field"><text class="dt">奋斗目标</text><text class="dd">{{ plan.struggle_goal || '—' }}</text></view>
          <view class="field"><text class="dt">高考要求</text><text class="dd">{{ plan.gaokao_requirement || '—' }}</text></view>
          <view class="field"><text class="dt">具体强化</text><text class="dd">{{ plan.reinforcement || '—' }}</text></view>
        </view>
      </view>

      <view v-if="active==='tasks'" class="panel">
        <EmptyState v-if="!detail.tasks.length" title="暂无任务" icon="📋" />
        <view v-for="task in detail.tasks" :key="task.id" class="task-card">
          <view class="task-head">
            <text class="subject-tag">{{ task.subject || '综合' }}</text>
            <text class="task-title">{{ task.title }}</text>
          </view>
          <text class="task-meta">{{ task.starts_on }} 至 {{ task.due_on }} · {{ task.status }}</text>
        </view>
        <view v-if="detail.task_checkins.length" class="checkin-section">
          <text class="section-h">执行记录</text>
          <Timeline :items="checkinItems" />
        </view>
      </view>

      <view v-if="active==='reviews'" class="panel">
        <EmptyState v-if="!detail.reviews.length" title="暂无督查复盘" icon="📋" />
        <Timeline v-else :items="reviewItems" />
      </view>
    </template>
    <EmptyState v-else title="暂无可查看档案" desc="班主任尚未发布可查看版本" icon="📭" />
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getMyCase } from '../../../api/studentCases'
import CaseStatusTag from '../../../components/CaseStatusTag.vue'
import Timeline from '../../../components/Timeline.vue'
import EmptyState from '../../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)
const active = ref('overview')
const tabs = [
  { key:'overview', label:'总览' },
  { key:'subjects', label:'学科' },
  { key:'tasks', label:'任务' },
  { key:'reviews', label:'复盘' },
]
const statusCopy = {
  executing: ['执行中', '当前版本由教师发布'],
  pending_review: ['待复盘', '已进入阶段复盘'],
  adjusted: ['已调整', '已生成新版本'],
  archived: ['已归档', '只读归档'],
}
const stateTitle = computed(() => statusCopy[detail.value?.status]?.[0] || detail.value?.status || '')
const stateDesc = computed(() => statusCopy[detail.value?.status]?.[1] || '')

const checkinItems = computed(() => (detail.value?.task_checkins || []).slice(0,20).map(c=>({
  title: `${c.completion_rate}% · ${taskTitle(c.task_id)}`,
  desc: c.self_check || '—',
  time: c.checked_in_at?.slice(0,16).replace('T',' '),
})))
const reviewItems = computed(() => (detail.value?.reviews || []).map(r=>({
  title: `${levelLabel(r.review_level)}${r.subject ? ' · '+r.subject : ''}`,
  desc: `${r.problem || ''}${r.corrective_action ? '｜整改：'+r.corrective_action : ''}${r.recheck_result ? '｜复查：'+r.recheck_result : ''}`,
  time: r.reviewed_at?.slice(0,16).replace('T',' '),
})))
function levelLabel(v){ return { school:'校级', principal:'校长', deyu:'德育', head_teacher:'班主任', subject:'学科'}[v] || v }
function taskTitle(id){ return detail.value?.tasks.find(t=>t.id===id)?.title || '任务' }

async function reload(){
  loading.value = true
  try { detail.value = await getMyCase() } catch(e){
    if (e.status !== 404) uni.showToast({ title: e.message || '加载失败', icon:'none' })
    detail.value = null
  } finally { loading.value = false }
}
onMounted(reload)
</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 16rpx; }
.head { display: flex; flex-direction: column; gap: 6rpx; }
.h1 { font-size: 32rpx; font-weight: 700; color: #1A1636; }
.p { font-size: 22rpx; color: #8E8B9E; }
.refresh-btn {
  align-self: flex-start; font-size: 22rpx; color: #6B5CE7;
  background: #F0EFFC; border: none; border-radius: 10rpx;
  padding: 8rpx 20rpx; margin-top: 4rpx;
}
.refresh-btn::after { border: none; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.header-card {
  background: #fff; border-radius: 20rpx; padding: 24rpx;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
}
.title-row { display: flex; gap: 12rpx; align-items: center; flex-wrap: wrap; }
.name { font-size: 30rpx; font-weight: 600; color: #1A1636; }
.meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 6rpx; }
.state-banner { margin-top: 12rpx; padding: 14rpx 16rpx; border-radius: 12rpx; background: #FAF9F7; }
.state-banner.is-executing { background: #F0FDF4; }
.state-title { font-size: 24rpx; font-weight: 600; color: #1A1636; display: block; }
.state-desc { font-size: 22rpx; color: #6E6B83; display: block; margin-top: 4rpx; }

.tabs { display: flex; gap: 10rpx; }
.tab {
  flex: 1; text-align: center; padding: 16rpx 0;
  font-size: 24rpx; color: #8E8B9E;
  background: #fff; border-radius: 14rpx;
  border: 2rpx solid #E8E6F0;
}
.tab.active {
  color: #6B5CE7; border-color: #D5D0F7;
  background: #F0EFFC; font-weight: 600;
}

.panel {
  background: #fff; border-radius: 20rpx; padding: 22rpx;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
  display: flex; flex-direction: column; gap: 16rpx;
}
.section { display: flex; flex-direction: column; gap: 6rpx; }
.section-muted { background: #FAF9F7; border-radius: 12rpx; padding: 16rpx; }
.section-h { font-size: 22rpx; font-weight: 600; color: #1A1636; }
.section-body { font-size: 24rpx; color: #4A4763; line-height: 1.7; white-space: pre-wrap; }

.plan-card {
  background: #FAF9F7; border-radius: 14rpx; padding: 18rpx;
  display: flex; flex-direction: column; gap: 8rpx;
}
.subject-chip {
  font-size: 20rpx; font-weight: 600; color: #6B5CE7;
  background: #EEEDFD; padding: 6rpx 14rpx; border-radius: 14rpx;
  align-self: flex-start;
}
.field { display: flex; flex-direction: column; gap: 2rpx; margin-top: 4rpx; }
.dt { font-size: 20rpx; color: #8E8B9E; }
.dd { font-size: 22rpx; color: #4A4763; line-height: 1.6; white-space: pre-wrap; }

.task-card {
  background: #FAF9F7; border-radius: 12rpx; padding: 16rpx;
}
.task-head { display: flex; gap: 10rpx; align-items: center; flex-wrap: wrap; }
.subject-tag {
  font-size: 18rpx; color: #6B5CE7; background: #EEEDFD;
  padding: 4rpx 10rpx; border-radius: 14rpx;
}
.task-title { font-size: 24rpx; font-weight: 600; color: #1A1636; }
.task-meta { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 6rpx; }
.checkin-section { margin-top: 8rpx; }
</style>
