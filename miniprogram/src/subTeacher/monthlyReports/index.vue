<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">月度评定</text>
      <text class="p">教师手动填写、审阅与发布月度评定</text>
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
        <text class="filter-label">状态</text>
        <picker :range="statusOptions" :value="statusIndex" @change="onStatusChange">
          <view class="picker-box">
            <text class="picker-text">{{ statusOptions[statusIndex] || '全部' }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>
    </view>

    <!-- 操作栏 -->
    <view class="action-bar">
      <button class="btn-primary" @click="goGenerate">新建评定</button>
      <button class="btn-outline" @click="loadData" :loading="loading" :disabled="loading">刷新</button>
    </view>

    <!-- 评定列表 -->
    <view class="card">
      <view v-if="loading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <EmptyState v-else-if="!reportList.length" title="暂无月度评定" desc="点击「新建评定」开始" />
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
          </view>
          <text class="report-arrow">›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listMonthlyReports } from '../../api/monthlyReports'
import { listClasses } from '../../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const classList = ref([])
const classIndex = ref(0)
const statusIndex = ref(0)
const statusOptions = ['全部', '待发布', '已发布', '待填写', '待补充']
const statusValues = ['', 'generated', 'published', 'generating', 'failed']
const reportList = ref([])

const classNames = computed(() => ['全部班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null)
const selectedStatus = computed(() => statusValues[statusIndex.value] || null)

function statusLabel(s) {
  return { generating: '待填写', generated: '待发布', published: '已发布', failed: '待补充' }[s] || s
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadClasses() {
  try { classList.value = await listClasses() } catch (e) { classList.value = [] }
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (selectedClassId.value) params.class_id = selectedClassId.value
    if (selectedStatus.value) params.status = selectedStatus.value
    reportList.value = await listMonthlyReports(params)
  } catch (e) {
    reportList.value = []
  } finally {
    loading.value = false
  }
}

function onClassChange(e) { classIndex.value = e.detail.value; loadData() }
function onStatusChange(e) { statusIndex.value = e.detail.value; loadData() }

function goGenerate() {
  if (!selectedClassId.value) {
    uni.showToast({ title: '请先选择班级', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/subTeacher/monthlyReports/generate?classId=${selectedClassId.value}` })
}

function goDetail(id) {
  uni.navigateTo({ url: `/subTeacher/monthlyReports/detail?id=${id}` })
}

onShow(() => {
  if (guardRole()) loadClasses().then(() => loadData())
})
</script>

<style scoped>
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
