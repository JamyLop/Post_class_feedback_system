<template>
  <view class="page">
    <view class="head">
      <text class="h1">周测成绩管理</text>
      <text class="p">录入与查看班级周测成绩</text>
    </view>

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
    </view>

    <!-- 操作栏 -->
    <view class="action-bar">
      <button class="btn-primary" @click="goCreate">录入成绩</button>
      <button class="btn-outline" @click="loadData" :loading="loading">刷新</button>
    </view>

    <!-- 班级汇总统计 -->
    <view v-if="summaryList.length" class="card">
      <text class="card-title">班级汇总</text>
      <view class="summary-list">
        <view v-for="(item, idx) in summaryList" :key="idx" class="summary-row" :class="{ 'has-border': idx > 0 }">
          <view class="summary-info">
            <text class="summary-name">{{ item.exam_name || item.subject }}</text>
            <text class="summary-date">{{ item.exam_date }}</text>
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
      <EmptyState v-else-if="!scoreList.length" title="暂无成绩记录" desc="点击上方「录入成绩」添加" icon="📊" />
      <view v-else class="score-list">
        <view v-for="(item, idx) in scoreList" :key="item.id" class="score-row" :class="{ 'has-border': idx > 0 }">
          <view class="score-info">
            <view class="score-head">
              <text class="student-name">{{ item.student_name || `学生#${item.student_id}` }}</text>
              <text class="subject-tag">{{ item.subject }}</text>
            </view>
            <text class="score-meta">{{ item.exam_name }} · {{ item.exam_date }}</text>
          </view>
          <view class="score-right">
            <text class="score-value">{{ item.score }}<text class="score-max">/{{ item.max_score }}</text></text>
            <text v-if="item.rank_in_class" class="rank-text">第{{ item.rank_in_class }}名</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listWeeklyScores, getClassSummary } from '../../api/weeklyScores'
import { listClasses } from '../../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const classList = ref([])
const classIndex = ref(0)
const subjectIndex = ref(0)
const subjectOptions = ['全部科目', '语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
const summaryList = ref([])
const scoreList = ref([])

const classNames = computed(() => ['全部班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null)
const selectedSubject = computed(() => subjectIndex.value > 0 ? subjectOptions[subjectIndex.value] : null)

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadClasses() {
  try {
    classList.value = await listClasses()
  } catch (e) {
    classList.value = []
  }
}

async function loadData() {
  if (!selectedClassId.value && classIndex.value > 0) return
  loading.value = true
  try {
    const params = {}
    if (selectedClassId.value) params.class_id = selectedClassId.value
    if (selectedSubject.value) params.subject = selectedSubject.value

    const [scores, summary] = await Promise.all([
      listWeeklyScores(params).catch(() => []),
      selectedClassId.value ? getClassSummary({ class_id: selectedClassId.value, subject: selectedSubject.value }).catch(() => []) : Promise.resolve([]),
    ])
    scoreList.value = Array.isArray(scores) ? scores : []
    summaryList.value = Array.isArray(summary) ? summary : []
  } finally {
    loading.value = false
  }
}

function onClassChange(e) {
  classIndex.value = e.detail.value
  loadData()
}

function onSubjectChange(e) {
  subjectIndex.value = e.detail.value
  loadData()
}

function goCreate() {
  if (!selectedClassId.value) {
    uni.showToast({ title: '请先选择班级', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/subTeacher/weeklyScores/create?classId=${selectedClassId.value}&className=${classNames.value[classIndex.value]}` })
}

onShow(() => {
  if (guardRole()) {
    loadClasses().then(() => loadData())
  }
})
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }

.filter-bar { display: flex; gap: 16rpx; }
.filter-item { flex: 1; display: flex; flex-direction: column; gap: 6rpx; }
.filter-label { font-size: 22rpx; font-weight: 500; color: #53666A; }
.picker-box {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1rpx solid #E0E7E5; border-radius: 8rpx;
  padding: 16rpx 18rpx;
}
.picker-text { font-size: 26rpx; color: #1A1636; }
.picker-arrow { font-size: 20rpx; color: #A09CB5; }

.action-bar { display: flex; gap: 16rpx; }
.btn-primary {
  flex: 2; background: #1F4F55; color: #fff; border-radius: 8rpx;
  padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; background: #fff; color: #1F4F55; border: 1rpx solid #B9CCCA;
  border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; margin-bottom: 14rpx; }

.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.summary-row { padding: 14rpx 0; }
.summary-row.has-border { border-top: 2rpx solid #F0EFFC; }
.summary-info { display: flex; align-items: center; gap: 12rpx; }
.summary-name { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.summary-date { font-size: 22rpx; color: #A09CB5; }
.summary-scores { display: flex; gap: 12rpx; margin-top: 10rpx; }
.score-chip {
  flex: 1; text-align: center; padding: 10rpx 0;
  border-radius: 8rpx; background: #F5F3EF;
}
.score-chip.avg { background: #E0F0E7; }
.score-chip.max { background: #EEEDFD; }
.score-chip.min { background: #F8E8B8; }
.score-num { font-size: 28rpx; font-weight: 700; color: #1A1636; display: block; }
.score-label { font-size: 18rpx; color: #6E6B83; display: block; margin-top: 2rpx; }

.score-row { padding: 16rpx 0; display: flex; align-items: center; justify-content: space-between; }
.score-row.has-border { border-top: 2rpx solid #F0EFFC; }
.score-info { flex: 1; }
.score-head { display: flex; align-items: center; gap: 10rpx; }
.student-name { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.subject-tag {
  font-size: 20rpx; color: #6B5CE7; background: #EEEDFD;
  padding: 4rpx 10rpx; border-radius: 14rpx;
}
.score-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
.score-right { text-align: right; }
.score-value { font-size: 30rpx; font-weight: 700; color: #1F4F55; }
.score-max { font-size: 22rpx; font-weight: 400; color: #A09CB5; }
.rank-text { font-size: 20rpx; color: #D97706; display: block; margin-top: 4rpx; }
</style>
