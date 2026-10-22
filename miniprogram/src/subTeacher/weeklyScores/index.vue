<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">月考成绩</text>
      <text class="p">{{ auth.role === 'subject_teacher' ? '查看所带班级对应学科的成绩与排名，可录入任教学科成绩' : '查看学生总分、各科成绩与排名' }}</text>
    </view>

    <view v-if="auth.role !== 'consultant'" class="view-tabs">
      <button :class="{ active: viewMode === 'overview' }" @click="viewMode = 'overview'">成绩总览与排名</button>
      <button :class="{ active: viewMode === 'records' }" @click="viewMode = 'records'">单科明细与评价</button>
    </view>
    <MonthlyExamOverview v-if="viewMode === 'overview'" ref="overviewRef" :classes="classList" />
    <!-- 小程序 hidden 属性会被 display:flex 覆盖，条件渲染保证两个视图互斥。 -->
    <view v-if="viewMode === 'records'" class="records-view">
    <!-- 筛选栏 -->
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
        <text class="filter-label">科目</text>
        <picker :range="subjectOptions" :value="subjectIndex" @change="onSubjectChange">
          <view class="picker-box">
            <text class="picker-text">{{ subjectOptions[subjectIndex] || '全部科目' }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
      <view class="filter-item">
        <text class="filter-label">月份</text>
        <picker mode="date" fields="month" :value="examMonth" @change="examMonth = $event.detail.value; loadData()">
          <view class="picker-box"><text>{{ examMonth || '全部月份' }}</text></view>
        </picker>
        <text v-if="examMonth" @click="examMonth = ''; loadData()">清除月份</text>
      </view>
    </view>

    <!-- 操作栏：德育主任/咨询老师仅只读查看，不展示录入入口 -->
    <view class="action-bar">
      <button v-if="canWrite" class="btn-primary" @click="goCreate">录入成绩</button>
      <button class="btn-outline" @click="onRefresh" :loading="loading" :disabled="loading">刷新</button>
    </view>

    <!-- 班级汇总统计 -->
    <view v-if="summaryList.length" class="card">
      <text class="card-title">班级汇总</text>
      <view class="summary-list">
        <view v-for="(item, idx) in summaryList" :key="idx" class="summary-row" :class="{ 'has-border': idx > 0 }">
          <view class="summary-info">
            <text class="summary-name">{{ item.subject }} · {{ item.exam_name || "月考" }}</text>
            <text class="summary-date">{{ item.exam_month }}</text>
          </view>
          <view class="summary-scores">
            <view class="score-chip avg">
              <text class="score-num">{{ item.avg_score }}</text>
              <text class="score-label">均分</text>
            </view>
            <view class="score-chip max">
              <text class="score-num">{{ item.max_score }}</text>
              <text class="score-label">最高</text>
            </view>
            <view class="score-chip min">
              <text class="score-num">{{ item.min_score }}</text>
              <text class="score-label">最低</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 成绩列表 -->
    <view class="card">
      <text class="card-title">成绩记录</text>
      <view v-if="loading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <EmptyState v-else-if="!scoreList.length" title="暂无成绩记录" :desc="canWrite ? '点击上方「录入成绩」添加' : '暂无可见的月考成绩'" />
      <view v-else class="score-list">
        <view v-for="(item, idx) in scoreList" :key="item.id" class="score-entry" :class="{ 'has-border': idx > 0 }">
          <view class="score-row">
          <view class="score-info">
            <view class="score-head">
              <text class="student-name">{{ item.student_name || `学生#${item.student_id}` }}</text>
              <text class="subject-tag">{{ item.subject }}</text>
            </view>
            <text class="score-meta">{{ item.exam_name }} · {{ item.exam_month }}</text>
          </view>
          <view class="score-right">
            <text class="score-value">{{ item.score }}<text class="score-max">/{{ item.max_score }}</text></text>
            <text v-if="item.rank_in_class" class="rank-text">第{{ item.rank_in_class }}名</text>
          </view>
          </view>
          <WeeklyScoreEvaluations :score="item" @saved="applyEvaluation" />
        </view>
      </view>
    </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import MonthlyExamOverview from '../../components/MonthlyExamOverview.vue'
import WeeklyScoreEvaluations from '../../components/WeeklyScoreEvaluations.vue'
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listWeeklyScores, getClassSummary, getMonthlyExamEntryOptions } from '../../api/weeklyScores'
import { listClasses } from '../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const viewMode = ref(auth.role === 'consultant' ? 'records' : 'overview')
const overviewRef = ref(null)
const loading = ref(false)
const classList = ref([])
const classIndex = ref(0)
const subjectIndex = ref(0)
const examMonth = ref('')
const subjectOptions = ['全部科目', '语文', '数学', '英语', '日语', '物理', '化学', '生物', '政治', '历史', '地理']
const summaryList = ref([])
const scoreList = ref([])

const classNames = computed(() => ['全部班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null)
const selectedSubject = computed(() => subjectIndex.value > 0 ? subjectOptions[subjectIndex.value] : null)

const entryScopes = ref([])
const canWrite = computed(() => selectedClassId.value
  ? entryScopes.value.some(s => s.class_id === selectedClassId.value)
  : entryScopes.value.length > 0)

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  // 德育主任全局督查、咨询老师查看关联学生，后端按角色过滤 scope
  if (!['teacher', 'admin', 'subject_teacher', 'deyu_director', 'consultant'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadClasses() {
  entryScopes.value = []
  try {
    const [classes, scopes] = await Promise.all([
      listClasses(),
      ['teacher', 'admin', 'subject_teacher'].includes(auth.role) ? getMonthlyExamEntryOptions() : Promise.resolve([]),
    ])
    classList.value = classes
    entryScopes.value = scopes
  } catch (e) {
    classList.value = []
    uni.showToast({ title: '班级加载失败，请点击刷新重试', icon: 'none' })
  }
}

async function loadData() {
  if (!selectedClassId.value && classIndex.value > 0) return
  loading.value = true
  try {
    const params = {}
    if (examMonth.value) params.exam_month = examMonth.value
    if (selectedClassId.value) params.class_id = selectedClassId.value
    if (selectedSubject.value) params.subject = selectedSubject.value

    const [scores, summary] = await Promise.all([
      listWeeklyScores(params),
      selectedClassId.value ? getClassSummary(params).catch(() => []) : Promise.resolve([]),
    ])
    scoreList.value = Array.isArray(scores) ? scores : []
    summaryList.value = Array.isArray(summary) ? summary : []
  } catch (error) {
    uni.showToast({ title: '月考成绩加载失败，请刷新重试', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function applyEvaluation(updated) {
  scoreList.value = scoreList.value.map(row => row.id === updated.id ? updated : row)
}

function onClassChange(e) {
  classIndex.value = Number(e.detail.value)
  loadData()
}

function onSubjectChange(e) {
  subjectIndex.value = Number(e.detail.value)
  loadData()
}

async function onRefresh() {
  // 班级为空时（德育主任曾反馈无法选择班级）先重拉班级，再查成绩，避免卡死空列表
  if (!classList.value.length) await loadClasses()
  await loadData()
}

function goCreate() {
  if (!selectedClassId.value) {
    uni.showToast({ title: '请先选择班级', icon: 'none' })
    return
  }
  if (!canWrite.value) return
  uni.navigateTo({ url: `/subTeacher/weeklyScores/create?classId=${selectedClassId.value}&className=${encodeURIComponent(classNames.value[classIndex.value])}` })
}

onShow(() => {
  if (guardRole()) {
    loadClasses().then(() => loadData())
    overviewRef.value?.load()
  }
})
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.records-view { display: flex; flex-direction: column; gap: 20rpx; }
.view-tabs { display: flex; gap: 12rpx; }
.view-tabs button { flex: 1; min-width: 0; margin: 0; padding: 16rpx 6rpx; font-size: 24rpx; line-height: 1.5; background: #fff; color: #445269; border-radius: 8rpx; }
.view-tabs button.active { color: #1762d4; background: #eaf3ff; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.filter-bar { display: flex; gap: 16rpx; }
.filter-item { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6rpx; }
.filter-label { font-size: 24rpx; font-weight: 500; color: #526177; }
.picker-box {
  display: flex; align-items: center; justify-content: space-between; gap: 8rpx;
  background: #fff; border: 1rpx solid var(--mp-line); border-radius: 8rpx;
  padding: 16rpx 18rpx; min-width: 0;
}
.picker-text { flex: 1; min-width: 0; font-size: 26rpx; color: var(--mp-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.picker-arrow { flex-shrink: 0; font-size: 24rpx; color: var(--mp-muted); }

.action-bar { display: flex; gap: 16rpx; }
.btn-primary {
  flex: 2; min-width: 0; width: 100%; box-sizing: border-box; background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 18rpx 8rpx; font-size: 28rpx; font-weight: 600; border: none; line-height: 1.5; min-height: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; min-width: 0; width: 100%; box-sizing: border-box; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE;
  border-radius: 8rpx; padding: 18rpx 8rpx; font-size: 28rpx; line-height: 1.5; min-height: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.btn-outline::after { border: none; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-bottom: 14rpx; }

.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.summary-row { padding: 14rpx 0; }
.summary-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.summary-info { display: flex; align-items: center; gap: 12rpx; }
.summary-name { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.summary-date { font-size: 24rpx; color: var(--mp-muted); }
.summary-scores { display: flex; gap: 12rpx; margin-top: 10rpx; }
.score-chip {
  flex: 1; text-align: center; padding: 10rpx 0;
  border-radius: 8rpx; background: #F3F5F8;
}
.score-chip.avg { background: #EAF3EE; }
.score-chip.max { background: var(--mp-soft); }
.score-chip.min { background: #FBF1DF; }
.score-num { font-size: 28rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.score-label { font-size: 18rpx; color: #526177; display: block; margin-top: 2rpx; }

.score-row { padding: 16rpx 0; display: flex; align-items: center; justify-content: space-between; gap: 12rpx; }
.score-entry { padding-bottom: 18rpx; }
.score-entry.has-border { border-top: 2rpx solid var(--mp-soft); }
.score-info { flex: 1; min-width: 0; }
.score-head { display: flex; align-items: center; gap: 10rpx; min-width: 0; }
.student-name { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.subject-tag {
  font-size: 24rpx; color: var(--mp-primary); background: var(--mp-soft);
  padding: 4rpx 10rpx; border-radius: 14rpx; flex-shrink: 0;
}
.score-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.score-right { text-align: right; flex-shrink: 0; }
.score-value { font-size: 30rpx; font-weight: 700; color: var(--mp-primary); }
.score-max { font-size: 24rpx; font-weight: 400; color: var(--mp-muted); }
.rank-text { font-size: 24rpx; color: #865C1E; display: block; margin-top: 4rpx; }
</style>
