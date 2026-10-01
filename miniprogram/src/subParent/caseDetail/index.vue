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
          <text class="suffix">学业发展总案</text>
        </view>
        <view class="meta">
          <CaseStatusTag :status="detail.status" />
          <text class="meta-text">{{ detail.class_name }} · 第{{ detail.version }}版</text>
        </view>
        <view class="state-banner" :class="`is-${detail.status}`">

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
          <EmptyState v-if="!detail.subject_plans.length" title="暂无学科方案" />
          <view v-for="plan in detail.subject_plans" :key="plan.id" class="plan-card">
            <view class="plan-head">
              <text class="subject-chip">{{ plan.subject }}</text>
              <text class="teacher-tip">{{ plan.teacher_name || '暂未填写教师姓名' }}</text>
            </view>
            <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
            <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
            <view class="field"><text class="dt">奋斗目标</text><text class="dd">{{ plan.struggle_goal || '—' }}</text></view>
            <view class="field"><text class="dt">高考要求</text><text class="dd">{{ plan.gaokao_requirement || '—' }}</text></view>
            <view class="field"><text class="dt">具体强化</text><text class="dd">{{ plan.reinforcement || '—' }}</text></view>
          </view>
        </view>

        <view v-if="active==='tasks'" class="tab-panel">
          <EmptyState v-if="!detail.tasks.length" title="暂无任务" />
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
            <!-- 需求：拍照打卡功能隐藏 -->
            <view v-if="false && checkinsWithPhotos.length" class="photo-section">
              <view v-for="c in checkinsWithPhotos" :key="c.id" class="photo-row">
                <text class="photo-title">{{ taskTitle(c.task_id) }} · {{ formatCheckinTime(c.checked_in_at) }} · 打卡照片</text>
                <CheckinAttachments :checkin-id="c.id" :attachments="c.attachments" />
              </view>
            </view>
          </view>
        </view>

        <view v-if="active==='reviews'" class="tab-panel">
          <EmptyState v-if="!detail.reviews.length" title="暂无督查复盘" />
          <Timeline v-else :items="reviewItems" />
        </view>

        <view v-if="active==='monthly'" class="tab-panel">
          <LoadState :loading="monthlyLoading" :error="monthlyError" @retry="loadMonthly" />
          <template v-if="!monthlyLoading && !monthlyError">
            <EmptyState v-if="!monthlyReports.length" title="暂无已发布月度评定" desc="班主任发布后即可在此查阅" />
            <view v-for="report in monthlyReports" :key="report.id" class="plan-card">
              <text class="section-h">{{ report.month_label }} 月度评定</text>
              <view class="field"><text class="dt">德育月度评定</text><text class="dd">{{ report.final_content || '暂无德育评定' }}</text></view>
              <view v-for="item in report.evaluations || []" :key="item.id" class="field">
                <text class="dt">{{ item.teacher_name || '老师' }} · {{ item.subject || '班主任' }}</text>
                <text class="dd">{{ item.content }}</text>
              </view>
            </view>
            <text v-if="monthlyReports.length" class="refresh-link" @click="loadMonthly">刷新月度评定</text>
          </template>
        </view>

        <view v-if="active==='exams'" class="tab-panel">
          <LoadState :loading="examsLoading" :error="examsError" @retry="loadExams" />
          <template v-if="!examsLoading && !examsError">
            <EmptyState v-if="!examScores.length" title="暂无月考成绩" desc="老师录入后即可在此查阅" />
            <view v-for="score in examScores" :key="score.id" class="plan-card">
              <view class="plan-head"><text class="subject-chip">{{ score.subject }}</text><text class="teacher-tip">{{ score.exam_month }}</text></view>
              <text class="section-h">{{ score.exam_name || '月考' }}</text>
              <text class="section-body">{{ score.score }} / {{ score.max_score }} 分 · 班级排名 {{ score.rank_in_class || '暂无' }}</text>
              <text class="teacher-tip">考试日期：{{ score.exam_date }}</text>
              <view v-if="score.remark" class="field"><text class="dt">备注</text><text class="dd">{{ score.remark }}</text></view>
              <view v-for="item in score.evaluations || []" :key="item.id" class="field">
                <text class="dt">{{ item.teacher_name || '老师' }} · {{ item.teacher_role === 'head_teacher' ? '班主任评价' : '学科评价' }}</text>
                <text class="dd">{{ item.content }}</text>
              </view>
            </view>
            <text v-if="examScores.length" class="refresh-link" @click="loadExams">刷新月考成绩</text>
          </template>
        </view>
      </view>
    </template>
    <EmptyState v-else title="档案不存在" desc="可能已被移除或无权查看" />
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase } from '../../api/studentCases'
import { listMonthlyReports } from '../../api/monthlyReports'
import { listWeeklyScores } from '../../api/weeklyScores'
import LoadState from '../../components/LoadState.vue'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import CheckinAttachments from '../../components/CheckinAttachments.vue'
import Timeline from '../../components/Timeline.vue'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)
const active = ref('overview')
const monthlyReports = ref([])
const examScores = ref([])
const monthlyLoading = ref(false)
const examsLoading = ref(false)
const monthlyError = ref('')
const examsError = ref('')
const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'subjects', label: '学科方案' },
  { key: 'tasks', label: '任务执行' },
  { key: 'reviews', label: '督查复盘' },
  { key: 'monthly', label: '月度评定' },
  { key: 'exams', label: '月考成绩' },
]

// 两个栏目独立加载，接口失败不能显示为“暂无数据”或阻断档案查阅。
async function loadMonthly() {
  if (!detail.value || monthlyLoading.value) return
  monthlyLoading.value = true
  monthlyError.value = ''
  try {
    monthlyReports.value = await loadAll(listMonthlyReports, { student_id: detail.value.student_id, status: 'published' })
  } catch (_) { monthlyError.value = '月度评定加载失败，请重试' }
  finally { monthlyLoading.value = false }
}
async function loadExams() {
  if (!detail.value || examsLoading.value) return
  examsLoading.value = true
  examsError.value = ''
  try {
    examScores.value = await loadAll(listWeeklyScores, { student_id: detail.value.student_id })
  } catch (_) { examsError.value = '月考成绩加载失败，请重试' }
  finally { examsLoading.value = false }
}
async function loadAll(fetchRows, params) {
  const rows = []
  for (let offset = 0; ; offset += 200) {
    const batch = await fetchRows({ ...params, limit: 200, offset })
    rows.push(...batch)
    if (batch.length < 200) return rows
  }
}
watch(active, value => {
  if (value === 'monthly') loadMonthly()
  if (value === 'exams') loadExams()
})

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
function formatCheckinTime(value) { return value?.slice(0, 16).replace('T', ' ') || '' }
const checkinsWithPhotos = computed(() => (detail.value?.task_checkins || []).filter(c => c.attachments?.length).slice(0, 20))
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
    if (active.value === 'monthly') await loadMonthly()
    if (active.value === 'exams') await loadExams()
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loading.value = false }
}

onShow(load)
</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.header-card {
  background: #fff; border-radius: 20rpx; padding: 28rpx;
  box-shadow: none;
}
.title-row { display: flex; gap: 12rpx; align-items: baseline; }
.h1 { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.suffix { font-size: 24rpx; color: var(--mp-muted); }
.meta { display: flex; gap: 12rpx; align-items: center; flex-wrap: wrap; margin-top: 10rpx; }
.meta-text { font-size: 24rpx; color: var(--mp-muted); }
.state-banner { margin-top: 14rpx; padding: 16rpx 18rpx; border-radius: 12rpx; background: #F7F8FA; }
.state-banner.is-executing { background: #F0FDF4; }
.state-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.state-desc { font-size: 24rpx; color: #526177; display: block; margin-top: 4rpx; }

.tabs {
  background: #fff; border-radius: 20rpx; overflow: hidden;
  box-shadow: none;
}
.tab-bar { display: flex; flex-wrap: wrap; border-bottom: 2rpx solid var(--mp-soft); }
.tab {
  flex: 0 0 33.333%; box-sizing: border-box; text-align: center; padding: 22rpx 0;
  font-size: 26rpx; color: var(--mp-muted);
  border-bottom: 4rpx solid transparent;
}
.tab.active { color: var(--mp-primary); border-bottom-color: var(--mp-primary); font-weight: 600; background: #F7F8FA; }
.tab-panel { padding: 24rpx; display: flex; flex-direction: column; gap: 18rpx; }

.section { display: flex; flex-direction: column; gap: 8rpx; }
.section-muted { background: #F7F8FA; border-radius: 12rpx; padding: 16rpx; }
.section-h { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.section-body { font-size: 26rpx; color: var(--mp-body); line-height: 1.7; white-space: pre-wrap; }

.plan-card {
  background: #F7F8FA; border-radius: 14rpx; padding: 20rpx;
  display: flex; flex-direction: column; gap: 10rpx;
}
.plan-head { display: flex; justify-content: space-between; align-items: center; }
.subject-chip {
  font-size: 24rpx; font-weight: 600; color: var(--mp-primary);
  background: var(--mp-soft); padding: 6rpx 16rpx; border-radius: 16rpx;
}
.teacher-tip { font-size: 24rpx; color: var(--mp-muted); }
.refresh-link { font-size: 26rpx; color: var(--mp-primary); padding: 16rpx 0; text-align: center; }
.field { display: flex; flex-direction: column; gap: 4rpx; margin-top: 4rpx; }
.dt { font-size: 24rpx; color: var(--mp-muted); }
.dd { font-size: 24rpx; color: var(--mp-body); line-height: 1.6; white-space: pre-wrap; }

.task-card {
  background: #F7F8FA; border-radius: 14rpx; padding: 20rpx;
}
.task-head { display: flex; gap: 12rpx; align-items: center; flex-wrap: wrap; }
.subject-tag {
  font-size: 24rpx; color: var(--mp-primary); background: var(--mp-soft);
  padding: 4rpx 12rpx; border-radius: 16rpx;
}
.task-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.task-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.task-link { font-size: 24rpx; color: var(--mp-primary); display: block; margin-top: 8rpx; }
.checkin-section { margin-top: 12rpx; }
.photo-section { margin-top: 14rpx; display: flex; flex-direction: column; gap: 12rpx; }
.photo-row { background: #F7F8FA; border-radius: 12rpx; padding: 14rpx; }
.photo-title { font-size: 22rpx; color: #526177; display: block; margin-bottom: 4rpx; }
</style>

<style scoped src="../../styles/details.css"></style>
