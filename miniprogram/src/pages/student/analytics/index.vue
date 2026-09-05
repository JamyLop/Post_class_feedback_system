<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">学情分析</text>
      <text class="p">周测成绩、变化趋势与月度评定</text>
      <view class="filter-row">
        <picker :range="subjectOptions" @change="onSubjectChange">
          <view class="filter-btn">
            <text class="filter-text">科目：{{ subject || '全部' }}</text>
            <text class="filter-arrow">›</text>
          </view>
        </picker>
        <button class="refresh-btn" size="mini" @click="reload">刷新</button>
      </view>
    </view>

    <view class="tabs">
      <text v-for="t in tabs" :key="t.key" class="tab" :class="{ active: active===t.key }" @click="active=t.key">{{ t.label }}</text>
    </view>

    <template v-if="active==='weekly'">
      <view v-if="weeklyLoading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <view v-else-if="weeklyRows.length" class="list">
        <view v-for="r in weeklyRows" :key="r.id" class="card">
          <view class="card-head">
            <text class="card-title">{{ r.exam_name || r.subject }} · {{ r.exam_date }}</text>
            <text class="score">{{ r.score }}/{{ r.max_score }}</text>
          </view>
          <text class="card-meta">{{ r.subject }} {{ r.class_name ? '· ' + r.class_name : '' }} {{ r.rank_in_class ? `· 班级排名 ${r.rank_in_class}` : '' }}</text>
          <text v-if="r.remark" class="card-remark">{{ r.remark }}</text>
          <WeeklyScoreEvaluations :score="r" />
        </view>
      </view>
      <EmptyState v-else title="暂无周测" desc="教师尚未录入周考成绩" />
    </template>

    <template v-if="active==='trend'">
      <view v-if="trendLoading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <view v-else-if="trendRows.length" class="list">
        <view class="trend-head">
          <text class="trend-title">{{ subject || '全科' }} 趋势 · {{ trendRows.length }} 次</text>
        </view>
        <view v-for="p in trendRows" :key="p.exam_date + p.exam_name" class="card">
          <text class="card-title">{{ p.exam_name || p.exam_date }}</text>
          <text class="card-meta">{{ p.exam_date }} · {{ p.score }}/{{ p.max_score }} · {{ percent(p.score, p.max_score) }}%</text>
          <view class="bar-wrap">
            <view class="bar" :style="{ width: percent(p.score, p.max_score) + '%' }"></view>
          </view>
        </view>
      </view>
      <EmptyState v-else title="暂无趋势" desc="选择科目后查看单科趋势" />
    </template>

    <template v-if="active==='monthly'">
      <view v-if="monthlyLoading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <view v-else-if="monthlyRows.length" class="list">
        <view v-for="r in monthlyRows" :key="r.id" class="card">
          <text class="card-title">{{ r.month_label || '月度评定' }}</text>
          <text class="card-meta">{{ r.month_label || r.created_at?.slice(0,7) || '' }} {{ r.class_name ? '· ' + r.class_name : '' }}</text>
          <text class="card-body">{{ (r.final_content || '').slice(0,160) || '—' }}</text>
        </view>
      </view>
      <EmptyState v-else title="暂无月度评定" desc="班主任尚未发布月度评定" />
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../../components/WorkspaceLink.vue'
import WeeklyScoreEvaluations from '../../../components/WeeklyScoreEvaluations.vue'
import { ref, onMounted, watch } from 'vue'
import { listWeeklyScores, getWeeklyTrend, listMonthlyReports } from '../../../api/assignments'
import { http } from '../../../utils/request'
import EmptyState from '../../../components/EmptyState.vue'

const tabs = [
  { key:'weekly', label:'周测' },
  { key:'trend', label:'趋势' },
  { key:'monthly', label:'月度' },
]
const active = ref('weekly')
const subject = ref('')
const subjectOptions = ['全部','语文','数学','英语','物理','化学','生物','政治','历史','地理']

const weeklyRows = ref([])
const trendRows = ref([])
const monthlyRows = ref([])
const weeklyLoading = ref(false)
const trendLoading = ref(false)
const monthlyLoading = ref(false)

function onSubjectChange(e) {
  const val = subjectOptions[e.detail.value]
  subject.value = val === '全部' ? '' : val
  reload()
}
function percent(score, max) {
  if (!max) return 0
  return Math.min(100, Math.max(0, Math.round((score / max) * 100)))
}

async function loadWeekly() {
  weeklyLoading.value = true
  try {
    const params = {}
    if (subject.value) params.subject = subject.value
    weeklyRows.value = await listWeeklyScores(params).catch(()=>[])
    if (!Array.isArray(weeklyRows.value)) weeklyRows.value = []
  } finally { weeklyLoading.value = false }
}
async function loadTrend() {
  trendLoading.value = true
  try {
    let sid = null
    try {
      const me = await http.get('/auth/me')
      if (me.role === 'student') sid = me.id
      else if (me.role === 'parent') {
        const kids = await http.get('/auth/me/children').catch(()=>[])
        sid = Array.isArray(kids) && kids[0]?.student_id
      }
    } catch(_) {}
    if (!sid) { trendRows.value = []; return }
    const params = { student_id: sid }
    if (subject.value) params.subject = subject.value
    trendRows.value = await getWeeklyTrend(params).catch(()=>[])
    if (!Array.isArray(trendRows.value)) trendRows.value = []
  } finally { trendLoading.value = false }
}
async function loadMonthly() {
  monthlyLoading.value = true
  try {
    monthlyRows.value = await listMonthlyReports(subject.value ? { subject: subject.value } : {}).catch(()=>[])
    if (!Array.isArray(monthlyRows.value)) monthlyRows.value = []
  } finally { monthlyLoading.value = false }
}
function reload() {
  if (active.value==='weekly') loadWeekly()
  if (active.value==='trend') loadTrend()
  if (active.value==='monthly') loadMonthly()
}
watch(active, reload)
onMounted(() => { loadWeekly(); loadTrend(); loadMonthly() })
</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 16rpx; }
.head { display: flex; flex-direction: column; gap: 6rpx; }
.h1 { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.p { font-size: 24rpx; color: var(--mp-muted); }
.filter-row { display: flex; gap: 12rpx; align-items: center; margin-top: 8rpx; }
.filter-btn {
  display: flex; align-items: center; gap: 6rpx;
  background: #fff; border: 2rpx solid var(--mp-line);
  border-radius: 12rpx; padding: 12rpx 18rpx;
}
.filter-text { font-size: 24rpx; color: var(--mp-ink); }
.filter-arrow { font-size: 24rpx; color: var(--mp-muted); }
.refresh-btn {
  font-size: 24rpx; color: var(--mp-primary);
  background: var(--mp-soft); border: none; border-radius: 10rpx;
}
.refresh-btn::after { border: none; }

.tabs { display: flex; gap: 10rpx; }
.tab {
  flex: 1; text-align: center; padding: 16rpx 0;
  font-size: 24rpx; color: var(--mp-muted);
  background: #fff; border-radius: 14rpx;
  border: 2rpx solid var(--mp-line);
}
.tab.active {
  color: var(--mp-primary); border-color: #B8C6D8;
  background: var(--mp-soft); font-weight: 600;
}

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.list { display: flex; flex-direction: column; gap: 12rpx; }

.card {
  background: #fff; border-radius: 18rpx; padding: 22rpx;
  box-shadow: none;
}
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.score { font-size: 28rpx; font-weight: 700; color: var(--mp-primary); }
.card-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.card-remark { font-size: 24rpx; color: #526177; display: block; margin-top: 8rpx; }
.card-body { font-size: 24rpx; color: #526177; display: block; margin-top: 8rpx; line-height: 1.6; white-space: pre-wrap; }

.trend-head { display: flex; justify-content: space-between; align-items: center; padding: 8rpx 0; }
.trend-title { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.bar-wrap { height: 12rpx; background: var(--mp-soft); border-radius: 999rpx; margin-top: 12rpx; overflow: hidden; }
.bar { height: 100%; background: var(--mp-primary); border-radius: 999rpx; }
</style>
