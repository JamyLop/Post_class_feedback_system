<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">积分周月报</text>
      <text class="p">打卡即得1分（单科单日封顶1分、单科周封顶7分），周任务按每周执行次数计入应得满分，一键生成班级周报、月报</text>
    </view>

    <view v-if="rows.length" class="class-points-banner">
      <view>
        <text class="banner-label">班主任：{{ headTeacherName }}</text>
        <text class="banner-title">本{{ periodType === 'weekly' ? '周' : '月' }}班级总积分</text>
      </view>
      <text class="class-total-points">{{ classTotalPoints }}<text class="points-unit"> 分</text></text>
    </view>

    <view class="filter-bar">
      <view class="filter-item">
        <text class="filter-label">班级</text>
        <picker :range="classNames" :value="classIndex" @change="onClassChange">
          <view class="picker-box">
            <text class="picker-text">{{ classNames[classIndex] || '选择班级' }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
      <view class="filter-item">
        <text class="filter-label">周期类型</text>
        <picker :range="typeOptions" :value="typeIndex" @change="onTypeChange">
          <view class="picker-box">
            <text class="picker-text">{{ typeOptions[typeIndex] }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
    </view>

    <view class="card">
      <view class="field">
        <text class="filter-label">{{ periodType === 'weekly' ? '周标签（如 2026-W36）' : '月份（如 2026-09）' }}</text>
        <input v-model="periodLabel" class="text-input" :placeholder="periodType === 'weekly' ? '2026-W36' : '2026-09'" @confirm="loadData" />
      </view>
      <view class="action-bar">
        <button class="btn-primary" :loading="building" :disabled="building || !selectedClassId" @click="build">一键生成本班报表</button>
        <button class="btn-outline" :loading="loading" :disabled="loading" @click="onRefresh">刷新</button>
      </view>
    </view>

    <view v-if="rows.length" class="card summary">
      <text class="card-title">本期汇总</text>
      <text class="summary-text">共 {{ rows.length }} 人 · 班均 {{ avgPoints }} 分 · 最高 {{ maxPoints }} 分（{{ topStudent }}）</text>
      <text class="summary-text muted">{{ periodRange }}</text>
    </view>

    <view class="card">
      <text class="card-title">积分榜</text>
      <view v-if="hasStaleRows" class="warn-bar">
        <text class="warn-text">存在旧口径报表（总分未按单科周封顶7分计算），请点击「一键生成本班报表」重新生成</text>
      </view>
      <view v-if="loading" class="loading-bar"><text class="loading-text">加载中...</text></view>
      <EmptyState v-else-if="!selectedClassId" title="请先选择班级" desc="选择班级后查看积分报表" />
      <EmptyState v-else-if="!rows.length" title="暂无积分报表" desc="确认周期后点击「一键生成本班报表」" />
      <view v-else class="report-list">
        <view v-for="(item, idx) in rows" :key="item.id" class="report-item" :class="{ 'has-border': idx > 0 }">
          <view class="report-row" @click="toggleExpand(item.id)">
            <view class="report-info">
              <view class="report-head">
                <text class="student-name">{{ item.student_name || `学生#${item.student_id}` }}</text>
                <text class="period-tag">{{ item.period_label }}</text>
              </view>
              <text class="report-meta">{{ item.class_name || '' }} · 任务 {{ item.task_count }} / 打卡 {{ item.checkin_count }}</text>
              <view class="progress-track"><view class="progress-fill" :style="{ width: `${Math.min(100, Number(item.completion_rate) || 0)}%` }" /></view>
            </view>
            <view class="report-score">
              <text class="score-value">{{ item.earned_points }}<text class="score-max">/{{ item.total_points }}</text></text>
              <text v-if="subjectBreakdown(item).length" class="score-sub">（{{ subjectBreakdown(item).length }}科，点看明细›）</text>
              <text v-if="isStaleRow(item)" class="stale-tag">旧口径</text>
              <text class="score-label">{{ item.completion_rate }}%</text>
            </view>
          </view>
          <view v-if="expandedId === item.id && subjectBreakdown(item).length" class="breakdown">
            <view v-for="s in subjectBreakdown(item)" :key="s.subject" class="breakdown-row">
              <text class="breakdown-subject">{{ s.subject || '综合' }}</text>
              <text class="breakdown-score">{{ s.earned }} / {{ s.total }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listPointsReports, buildPointsReports } from '../../api/pointsReports'
import { listClasses } from '../../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const building = ref(false)
const classList = ref([])
const classIndex = ref(0)
const typeIndex = ref(0)
const typeOptions = ['周报', '月报']
const typeValues = ['weekly', 'monthly']
const periodLabel = ref('')
const rows = ref([])
const expandedId = ref(null)

// 当前积分口径版本（与后端 POINTS_RULE / Web 端 CURRENT_POINTS_RULE 同步）
const CURRENT_POINTS_RULE = 'daily-1-point_subject-weekly-cap-7'
const isStaleRow = (row) => ((row && row.detail && row.detail.rule) || '') !== CURRENT_POINTS_RULE
const hasStaleRows = computed(() => rows.value.some(isStaleRow))
// 分科明细：分母是各科封顶之和，点行展开查看（旧口径行无分科数据则不可展开）
const subjectBreakdown = (row) => {
  const earned = (row && row.detail && row.detail.per_subject_earned) || {}
  const total = (row && row.detail && row.detail.per_subject_total) || {}
  const keys = [...new Set([...Object.keys(earned), ...Object.keys(total)])]
  return keys
    .map((k) => ({ subject: k, earned: earned[k] ?? 0, total: total[k] ?? '-' }))
    .sort((a, b) => b.earned - a.earned)
}
function toggleExpand(id) {
  const row = rows.value.find((r) => r.id === id)
  if (!row || !subjectBreakdown(row).length) return
  expandedId.value = expandedId.value === id ? null : id
}

const classNames = computed(() => ['选择班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => (classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null))
const periodType = computed(() => typeValues[typeIndex.value])

const avgPoints = computed(() => {
  if (!rows.value.length) return 0
  return Math.round((rows.value.reduce((s, r) => s + (Number(r.earned_points) || 0), 0) / rows.value.length) * 100) / 100
})
const maxPoints = computed(() => (rows.value.length ? Math.max(...rows.value.map(r => Number(r.earned_points) || 0)) : 0))
const topStudent = computed(() => rows.value.find(r => (Number(r.earned_points) || 0) === maxPoints.value)?.student_name || '-')
const classTotalPoints = computed(() => Math.round(rows.value.reduce((sum, row) => sum + (Number(row.earned_points) || 0), 0) * 100) / 100)
const headTeacherName = computed(() => rows.value[0]?.head_teacher_name || '班主任')
const periodRange = computed(() => {
  const first = rows.value[0]
  return first ? `${first.period_start || ''} ~ ${first.period_end || ''}` : ''
})

function currentWeekLabel() {
  const now = new Date()
  const thursday = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))
  const day = (thursday.getUTCDay() + 6) % 7
  thursday.setUTCDate(thursday.getUTCDate() - day + 3)
  const firstThursday = new Date(Date.UTC(thursday.getUTCFullYear(), 0, 4))
  const week = 1 + Math.round(((thursday - firstThursday) / 86400000 - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7)
  return `${thursday.getUTCFullYear()}-W${String(week).padStart(2, '0')}`
}
function currentMonthLabel() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  // 与 Web 端一致：仅班主任 / 德育主任 / 管理员可见，学生、家长、咨询、任课老师由后端 403
  if (!['teacher', 'admin', 'deyu_director'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限查看积分', icon: 'none' })
    uni.reLaunch({ url: '/pages/index/index' })
    return false
  }
  return true
}

function onClassChange(e) {
  classIndex.value = Number(e.detail.value)
  loadData()
}

function onTypeChange(e) {
  typeIndex.value = Number(e.detail.value)
  periodLabel.value = periodType.value === 'weekly' ? currentWeekLabel() : currentMonthLabel()
  loadData()
}

async function reloadClasses() {
  try {
    classList.value = await listClasses()
  } catch (_) {
    classList.value = []
    uni.showToast({ title: '班级加载失败，请点击刷新重试', icon: 'none' })
  }
}

async function onRefresh() {
  // 班级为空时先重拉班级，再查报表，避免picker长期只有“选择班级”一项
  if (!classList.value.length) await reloadClasses()
  await loadData()
}

async function loadData() {
  if (!selectedClassId.value) { rows.value = []; return }
  loading.value = true
  try {
    const data = await listPointsReports({
      class_id: selectedClassId.value,
      period_type: periodType.value,
      period_label: periodLabel.value || undefined,
    })
    rows.value = Array.isArray(data) ? data : []
  } catch (e) {
    // 403 等错误已由 request 统一提示
  } finally {
    loading.value = false
  }
}

async function build() {
  if (!selectedClassId.value) {
    uni.showToast({ title: '请先选择班级', icon: 'none' })
    return
  }
  building.value = true
  try {
    const data = await buildPointsReports({
      class_id: selectedClassId.value,
      period_type: periodType.value,
      period_label: periodLabel.value || undefined,
    })
    rows.value = Array.isArray(data) ? data : []
    uni.showToast({ title: `已生成 ${rows.value.length} 名学生${periodType.value === 'weekly' ? '周报' : '月报'}`, icon: 'success' })
  } catch (e) {
    // 错误已统一提示
  } finally {
    building.value = false
  }
}

onShow(async () => {
  if (!guardRole()) return
  await reloadClasses()
  if (!periodLabel.value) periodLabel.value = currentWeekLabel()
  if (classList.value.length && classIndex.value === 0) {
    const g3 = classList.value.findIndex(c => c.grade === '高三')
    classIndex.value = g3 >= 0 ? g3 + 1 : 1
  }
  loadData()
})
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; line-height: 1.6; }
.class-points-banner { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; padding: 26rpx 28rpx; border-radius: 16rpx; color: #fff; background: linear-gradient(120deg, #1E40AF, #2563EB); }
.banner-label { display: block; margin-bottom: 8rpx; color: #BFDBFE; font-size: 24rpx; font-weight: 600; }
.banner-title { display: block; font-size: 30rpx; font-weight: 700; }
.class-total-points { flex-shrink: 0; font-size: 48rpx; font-weight: 750; }
.points-unit { font-size: 26rpx; font-weight: 400; }
.filter-bar { display: flex; gap: 16rpx; }
.filter-item { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6rpx; }
.filter-label { font-size: 24rpx; font-weight: 500; color: #526177; }
.picker-box { display: flex; align-items: center; justify-content: space-between; gap: 8rpx; background: #fff; border: 1rpx solid var(--mp-line); border-radius: 8rpx; padding: 16rpx 18rpx; min-width: 0; }
.picker-text { flex: 1; min-width: 0; font-size: 26rpx; color: var(--mp-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.picker-arrow { flex-shrink: 0; font-size: 24rpx; color: var(--mp-muted); }
.card { background: #fff; border-radius: 10rpx; padding: 24rpx; border: 1rpx solid var(--mp-line); display: flex; flex-direction: column; gap: 16rpx; }
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.field { display: flex; flex-direction: column; gap: 8rpx; min-width: 0; }
.text-input { background: #F7F8FA; border: 1rpx solid var(--mp-line); border-radius: 8rpx; padding: 16rpx 18rpx; font-size: 26rpx; min-height: 72rpx; line-height: 1.5; box-sizing: border-box; width: 100%; }
.action-bar { display: flex; gap: 16rpx; }
.btn-primary { flex: 2; min-width: 0; width: 100%; box-sizing: border-box; background: var(--mp-primary); color: #fff; border-radius: 8rpx; padding: 18rpx 8rpx; font-size: 28rpx; font-weight: 600; border: none; line-height: 1.5; min-height: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.btn-primary::after { border: none; }
.btn-outline { flex: 1; min-width: 0; width: 100%; box-sizing: border-box; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 8rpx; font-size: 28rpx; line-height: 1.5; min-height: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.btn-outline::after { border: none; }
.summary-text { font-size: 26rpx; color: var(--mp-ink); display: block; }
.summary-text.muted { color: var(--mp-muted); font-size: 24rpx; }
.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.report-row { display: flex; align-items: center; gap: 16rpx; padding: 14rpx 0; }
.report-item.has-border { border-top: 2rpx solid var(--mp-soft); }
.report-info { flex: 1; min-width: 0; }
.report-head { display: flex; align-items: center; gap: 10rpx; min-width: 0; }
.student-name { font-size: 27rpx; font-weight: 600; color: var(--mp-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.period-tag { flex-shrink: 0; font-size: 22rpx; color: var(--mp-muted); background: #F3F5F8; padding: 4rpx 12rpx; border-radius: 12rpx; }
.report-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.progress-track { height: 10rpx; background: #EDF1F7; border-radius: 6rpx; margin-top: 10rpx; overflow: hidden; }
.progress-fill { height: 100%; background: var(--mp-primary); border-radius: 6rpx; }
.report-score { text-align: right; flex-shrink: 0; }
.score-value { font-size: 30rpx; font-weight: 700; color: var(--mp-primary); display: block; }
.score-max { font-size: 24rpx; font-weight: 400; color: var(--mp-muted); }
.score-sub { font-size: 22rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.stale-tag { font-size: 20rpx; color: #B45309; background: #FEF3C7; border: 1rpx solid #FCD34D; padding: 2rpx 10rpx; border-radius: 10rpx; display: inline-block; margin-top: 4rpx; }
.score-label { font-size: 22rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.warn-bar { background: #FFFBEB; border: 1rpx solid #FDE68A; border-radius: 8rpx; padding: 16rpx 18rpx; }
.warn-text { font-size: 24rpx; color: #92400E; line-height: 1.6; display: block; }
.breakdown { background: #F7F8FA; border-radius: 10rpx; padding: 12rpx 16rpx; margin: 8rpx 0 12rpx; display: flex; flex-direction: column; gap: 6rpx; }
.breakdown-row { display: flex; justify-content: space-between; align-items: center; }
.breakdown-subject { font-size: 24rpx; color: var(--mp-muted); }
.breakdown-score { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
</style>
