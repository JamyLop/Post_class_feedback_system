<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">积分周月报</text>
      <text class="p">阶段任务每日记录后，按完成度累加积分，一键生成班级周报、月报</text>
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
        <button class="btn-outline" :loading="loading" :disabled="loading" @click="loadData">刷新</button>
      </view>
    </view>

    <view v-if="rows.length" class="card summary">
      <text class="card-title">本期汇总</text>
      <text class="summary-text">共 {{ rows.length }} 人 · 班均 {{ avgPoints }} 分 · 最高 {{ maxPoints }} 分（{{ topStudent }}）</text>
      <text class="summary-text muted">{{ periodRange }}</text>
    </view>

    <view class="card">
      <text class="card-title">积分榜</text>
      <view v-if="loading" class="loading-bar"><text class="loading-text">加载中...</text></view>
      <EmptyState v-else-if="!selectedClassId" title="请先选择班级" desc="选择班级后查看积分报表" />
      <EmptyState v-else-if="!rows.length" title="暂无积分报表" desc="确认周期后点击「一键生成本班报表」" />
      <view v-else class="report-list">
        <view v-for="(item, idx) in rows" :key="item.id" class="report-row" :class="{ 'has-border': idx > 0 }">
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
            <text class="score-label">{{ item.completion_rate }}%</text>
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

const classNames = computed(() => ['选择班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => (classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null))
const periodType = computed(() => typeValues[typeIndex.value])

const avgPoints = computed(() => {
  if (!rows.value.length) return 0
  return Math.round((rows.value.reduce((s, r) => s + (Number(r.earned_points) || 0), 0) / rows.value.length) * 100) / 100
})
const maxPoints = computed(() => (rows.value.length ? Math.max(...rows.value.map(r => Number(r.earned_points) || 0)) : 0))
const topStudent = computed(() => rows.value.find(r => (Number(r.earned_points) || 0) === maxPoints.value)?.student_name || '-')
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
  try {
    classList.value = await listClasses()
  } catch (_) {
    classList.value = []
  }
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
.filter-bar { display: flex; gap: 16rpx; }
.filter-item { flex: 1; display: flex; flex-direction: column; gap: 6rpx; }
.filter-label { font-size: 24rpx; font-weight: 500; color: #526177; }
.picker-box { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1rpx solid var(--mp-line); border-radius: 8rpx; padding: 16rpx 18rpx; }
.picker-text { font-size: 26rpx; color: var(--mp-ink); }
.picker-arrow { font-size: 24rpx; color: var(--mp-muted); }
.card { background: #fff; border-radius: 10rpx; padding: 24rpx; border: 1rpx solid var(--mp-line); display: flex; flex-direction: column; gap: 16rpx; }
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.text-input { background: #F7F8FA; border: 1rpx solid var(--mp-line); border-radius: 8rpx; padding: 16rpx 18rpx; font-size: 26rpx; }
.action-bar { display: flex; gap: 16rpx; }
.btn-primary { flex: 2; background: var(--mp-primary); color: #fff; border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none; }
.btn-primary::after { border: none; }
.btn-outline { flex: 1; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx; }
.btn-outline::after { border: none; }
.summary-text { font-size: 26rpx; color: var(--mp-ink); display: block; }
.summary-text.muted { color: var(--mp-muted); font-size: 24rpx; }
.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.report-row { display: flex; align-items: center; gap: 16rpx; padding: 14rpx 0; }
.report-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.report-info { flex: 1; min-width: 0; }
.report-head { display: flex; align-items: center; gap: 10rpx; }
.student-name { font-size: 27rpx; font-weight: 600; color: var(--mp-ink); }
.period-tag { font-size: 22rpx; color: var(--mp-muted); background: #F3F5F8; padding: 4rpx 12rpx; border-radius: 12rpx; }
.report-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.progress-track { height: 10rpx; background: #EDF1F7; border-radius: 6rpx; margin-top: 10rpx; overflow: hidden; }
.progress-fill { height: 100%; background: var(--mp-primary); border-radius: 6rpx; }
.report-score { text-align: right; flex-shrink: 0; }
.score-value { font-size: 30rpx; font-weight: 700; color: var(--mp-primary); display: block; }
.score-max { font-size: 24rpx; font-weight: 400; color: var(--mp-muted); }
.score-label { font-size: 22rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
</style>
