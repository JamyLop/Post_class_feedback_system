<template>
  <view class="page">
    <view class="head">
      <text class="h1">月度评价</text>
      <text class="p">AI 生成学生月度综合评价</text>
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
      <button class="btn-primary" @click="goGenerate">生成评价</button>
      <button class="btn-outline" @click="loadData" :loading="loading">刷新</button>
    </view>

    <!-- 评价列表 -->
    <view class="card">
      <view v-if="loading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
      <EmptyState v-else-if="!reportList.length" title="暂无月度评价" desc="点击「生成评价」开始" icon="📋" />
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
const statusOptions = ['全部', '已生成', '已发布', '生成中', '失败']
const statusValues = ['', 'generated', 'published', 'generating', 'failed']
const reportList = ref([])

const classNames = computed(() => ['全部班级', ...classList.value.map(c => c.name)])
const selectedClassId = computed(() => classIndex.value > 0 ? classList.value[classIndex.value - 1]?.id : null)
const selectedStatus = computed(() => statusValues[statusIndex.value] || null)

function statusLabel(s) {
  return { generating: '生成中', generated: '已生成', published: '已发布', failed: '失败' }[s] || s
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
.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.report-row {
  padding: 18rpx 0; display: flex; align-items: center; justify-content: space-between;
}
.report-row.has-border { border-top: 2rpx solid #F0EFFC; }
.report-info { flex: 1; }
.report-head { display: flex; align-items: center; gap: 10rpx; }
.student-name { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.status-tag {
  padding: 4rpx 12rpx; border-radius: 14rpx;
  font-size: 20rpx; font-weight: 500;
}
.status-tag.is-generated { background: #E0F0E7; color: #2E7D5B; }
.status-tag.is-published { background: #EEEDFD; color: #6B5CE7; }
.status-tag.is-generating { background: #F8E8B8; color: #8A641C; }
.status-tag.is-failed { background: #F7E0D9; color: #9C4E3F; }
.status-text { white-space: nowrap; }
.report-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
.report-preview { font-size: 22rpx; color: #6E6B83; display: block; margin-top: 6rpx; line-height: 1.5; }
.report-arrow { font-size: 32rpx; color: #739095; font-weight: 600; margin-left: 12rpx; }
</style>
