<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">月度评定</text>
      <text class="p">{{ isSubjectTeacher ? '对应老师填写学科总结、问题、计划' : '教师手动填写、审阅与发布月度评定' }}</text>
    </view>

    <view v-if="canQueryWriting" class="query-tabs">
      <button :class="{ active: activeTab === 'writing' }" @click="activeTab = 'writing'">填写状态查询</button>
      <button :class="{ active: activeTab === 'reports' }" @click="activeTab = 'reports'">评定列表</button>
    </view>
    <MonthlyWritingStatus v-if="activeTab === 'writing'" :key="auth.user?.supervisor_stage || ''" ref="writingQuery" :classes="classList" />
    <template v-if="activeTab === 'reports'">
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
        <text class="filter-label">状态</text>
        <picker :range="statusOptions" :value="statusIndex" @change="onStatusChange">
          <view class="picker-box">
            <text class="picker-text">{{ statusOptions[statusIndex] || '全部' }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
    </view>

    <!-- 操作栏：任课老师仅评价，不展示新建入口 -->
    <view class="action-bar">
      <button class="btn-primary" @click="goGenerate">新建评定</button>
      <button class="btn-outline" @click="refreshPage" :loading="loading" :disabled="loading">刷新</button>
    </view>

    <!-- 评定列表 -->
    <view class="card">
      <view v-if="loading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <EmptyState v-else-if="!reportList.length" :title="isSubjectTeacher ? '暂无所带班级的月度评定' : '暂无月度评定'" :desc="isSubjectTeacher ? '点击「新建评定」开始填写对应学科' : '点击「新建评定」开始'" />
      <view v-else class="report-list">
        <view v-for="(item, idx) in reportList" :key="item.id" class="report-row" :class="{ 'has-border': idx > 0 }" @click="goDetail(item.id)">
          <view class="report-info">
            <view class="report-head">
              <text class="student-name">{{ item.student_name || `学生#${item.student_id}` }}</text>
              <view class="status-tag" :class="`is-${item.status}`">
                <text class="status-text">{{ statusLabel(item.status) }}</text>
              </view>
            </view>
            <text class="report-meta">{{ item.month_label }} · {{ item.class_name || '' }}</text>
            <text v-if="item.final_content" class="report-preview">{{ item.final_content.slice(0, 60) }}...</text>
            <MonthlyReportEvaluations :report="item" @saved="applyEvaluation" @click.stop />
          </view>
          <text class="report-arrow">›</text>
        </view>
      </view>
    </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import MonthlyWritingStatus from '../../components/MonthlyWritingStatus.vue'
import MonthlyReportEvaluations from '../../components/MonthlyReportEvaluations.vue'
import { ref, computed, nextTick, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listMonthlyReports } from '../../api/monthlyReports'
import { listSupervisionClasses } from '../../api/studentCases'
import { listClasses } from '../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const canQueryWriting = ['teacher', 'subject_teacher'].includes(auth.role)
const activeTab = ref(canQueryWriting ? 'writing' : 'reports')
const writingQuery = ref(null)
const loading = ref(false)
const classList = ref([])
const teachingClassList = ref([])
const classIndex = ref(0)
const statusIndex = ref(0)
const statusOptions = ['全部', '待发布', '已发布', '待填写', '待补充']
const statusValues = ['', 'generated', 'published', 'generating', 'failed']
const reportList = ref([])
let classesRequestId = 0
let reportsRequestId = 0
let pageReady = false
let refreshingIdentity = false

const classNames = computed(() => ['全部班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null)
const selectedStatus = computed(() => statusValues[statusIndex.value] || null)
const isSubjectTeacher = computed(() => auth.role === 'subject_teacher')

function statusLabel(s) {
  return { generating: '待填写', generated: '待发布', published: '已发布', failed: '待补充' }[s] || s
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'admin', 'subject_teacher'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadClasses() {
  const requestId = ++classesRequestId
  const selectedId = selectedClassId.value
  const stage = auth.user?.supervisor_stage || ''
  const [own, stageClasses] = await Promise.all([
    listClasses().catch(() => []),
    stage ? listSupervisionClasses().catch(() => []) : Promise.resolve([]),
  ])
  if (requestId !== classesRequestId) return false
  teachingClassList.value = own
  const seen = new Set()
  classList.value = [...stageClasses, ...own].filter(c => !seen.has(c.id) && seen.add(c.id))
  // 扩大或收回查看范围后，picker 的旧下标不能指向另一个班。
  classIndex.value = selectedId ? classList.value.findIndex(c => c.id === selectedId) + 1 : 0
  return true
}

async function loadData() {
  const requestId = ++reportsRequestId
  writingQuery.value?.load()
  loading.value = true
  try {
    const params = {}
    if (selectedClassId.value) params.class_id = selectedClassId.value
    if (selectedStatus.value) params.status = selectedStatus.value
    const data = await listMonthlyReports(params)
    if (requestId === reportsRequestId) reportList.value = data
  } catch (e) {
    if (requestId === reportsRequestId) reportList.value = []
  } finally {
    if (requestId === reportsRequestId) loading.value = false
  }
}

function onClassChange(e) { classIndex.value = e.detail.value; loadData() }
function onStatusChange(e) { statusIndex.value = e.detail.value; loadData() }

function applyEvaluation(updated) {
  reportList.value = reportList.value.map(row => row.id === updated.id ? updated : row)
}

function goGenerate() {
  if (!selectedClassId.value) {
    uni.showToast({ title: '请先选择班级', icon: 'none' })
    return
  }
  if (!teachingClassList.value.some(c => c.id === selectedClassId.value)) {
    uni.showToast({ title: '只能为自己任教的班级填写评定', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/subTeacher/monthlyReports/generate?classId=${selectedClassId.value}` })
}

function goDetail(id) {
  uni.navigateTo({ url: `/subTeacher/monthlyReports/detail?id=${id}` })
}

async function reloadScope() {
  if (!await loadClasses()) return
  await nextTick()
  await loadData()
}

async function refreshPage() {
  if (!guardRole()) return
  refreshingIdentity = true
  try {
    // 每次回到页面都同步身份，避免继续使用授权变更前的缓存。
    await auth.refreshMe()
  } catch {
    uni.showToast({ title: '身份信息刷新失败，请重试', icon: 'none' })
    return
  } finally {
    refreshingIdentity = false
  }
  if (!guardRole()) return
  pageReady = true
  await reloadScope()
}

watch(() => auth.user?.supervisor_stage || '', () => {
  classIndex.value = 0
  if (pageReady && !refreshingIdentity) reloadScope()
})
onShow(refreshPage)
</script>

<style scoped>
.query-tabs { display: flex; border-bottom: 1rpx solid var(--mp-line); }
.query-tabs button { flex: 1; margin: 0; border-radius: 0; background: transparent; color: var(--mp-body, #445269); font-size: 28rpx; }
.query-tabs button::after { border: 0; }
.query-tabs button.active { color: var(--mp-primary); border-bottom: 4rpx solid var(--mp-primary); }
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.filter-bar { display: flex; gap: 16rpx; }
.filter-item { flex: 1; display: flex; flex-direction: column; gap: 6rpx; }
.filter-label { font-size: 24rpx; font-weight: 500; color: #526177; }
.picker-box {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1rpx solid var(--mp-line); border-radius: 8rpx;
  padding: 16rpx 18rpx;
}
.picker-text { font-size: 26rpx; color: var(--mp-ink); }
.picker-arrow { font-size: 24rpx; color: var(--mp-muted); }

.action-bar { display: flex; gap: 16rpx; }
.btn-primary {
  flex: 2; background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE;
  border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.report-row {
  padding: 18rpx 0; display: flex; align-items: center; justify-content: space-between;
}
.report-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.report-info { flex: 1; }
.report-head { display: flex; align-items: center; gap: 10rpx; }
.student-name { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.status-tag {
  padding: 4rpx 12rpx; border-radius: 14rpx;
  font-size: 24rpx; font-weight: 500;
}
.status-tag.is-generated { background: #EAF3EE; color: #286349; }
.status-tag.is-published { background: var(--mp-soft); color: var(--mp-primary); }
.status-tag.is-generating { background: #FBF1DF; color: #865C1E; }
.status-tag.is-failed { background: #FAECE9; color: #A33E39; }
.status-text { white-space: nowrap; }
.report-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.report-preview { font-size: 24rpx; color: #526177; display: block; margin-top: 6rpx; line-height: 1.5; }
.report-arrow { font-size: 32rpx; color: var(--mp-muted); font-weight: 600; margin-left: 12rpx; }
</style>
