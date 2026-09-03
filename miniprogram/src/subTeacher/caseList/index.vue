<template>
  <view class="page">
    <view class="filters">
      <picker :range="classOptions" range-key="name" @change="onClassChange">
        <view class="filter-btn">
          <text class="filter-icon">📁</text>
          <text class="filter-text">{{ selectedClassName }}</text>
          <text class="filter-arrow">›</text>
        </view>
      </picker>
      <picker :range="statusOptions" range-key="label" @change="onStatusChange">
        <view class="filter-btn">
          <text class="filter-icon">🏷️</text>
          <text class="filter-text">{{ selectedStatusLabel }}</text>
          <text class="filter-arrow">›</text>
        </view>
      </picker>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view v-if="selectedClassId && students.length" class="card">
        <text class="card-title">学生（{{ students.length }}）</text>
        <view v-for="(s, idx) in students" :key="s.id" class="student-row" :class="{ 'has-border': idx > 0 }" @click="openStudentCases(s)">
          <view class="student-avatar">{{ (s.name || '?').slice(0,1) }}</view>
          <view class="student-info">
            <text class="student-name">{{ s.name }}</text>
            <text class="student-meta">{{ s.username }}</text>
          </view>
          <text class="arrow">›</text>
        </view>
      </view>

      <view v-if="rows.length" class="card">
        <text class="card-title">{{ selectedClassId ? '档案' : '全部档案' }}（{{ rows.length }}）</text>
        <view v-for="(c, idx) in rows" :key="c.id" class="case-row" :class="{ 'has-border': idx > 0 }" @click="openDetail(c.id)">
          <view class="case-info">
            <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
            <text class="case-meta">{{ c.class_name }} · 第{{ c.version }}版 · {{ (c.updated_at||'').slice(0,10) }}</text>
          </view>
          <CaseStatusTag :status="c.status" />
        </view>
      </view>

      <EmptyState v-if="!rows.length && !students.length" title="暂无档案" desc="请在 Web 端新建学生档案" />
    </template>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases, listClasses, listClassStudents } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const rows = ref([])
const classes = ref([])
const students = ref([])
const selectedClassId = ref(null)
const selectedStatus = ref(null)

const classOptions = computed(() => [{ id: null, name: '全部班级' }, ...classes.value])
const selectedClassName = computed(() => classOptions.value.find(c => c.id === selectedClassId.value)?.name || '全部班级')

const statusOptions = [
  { value: null, label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'pending_confirmation', label: '待审查' },
  { value: 'revision_required', label: '待整改' },
  { value: 'executing', label: '执行中' },
  { value: 'pending_review', label: '待复盘' },
  { value: 'adjusted', label: '已调整' },
  { value: 'archived', label: '已归档' },
]
const selectedStatusLabel = computed(() => statusOptions.find(s => s.value === selectedStatus.value)?.label || '全部状态')

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'deyu_director', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadClasses() {
  try {
    const list = await listClasses()
    classes.value = Array.isArray(list) ? list : []
  } catch (_) { classes.value = [] }
}

async function loadCases() {
  loading.value = true
  students.value = []
  try {
    const params = {}
    if (selectedClassId.value) params.class_id = selectedClassId.value
    if (selectedStatus.value) params.status = selectedStatus.value
    rows.value = await listStudentCases(params)
  } catch (_) { rows.value = [] } finally { loading.value = false }
}

async function loadStudents(classId) {
  if (!classId) { students.value = []; return }
  try {
    const list = await listClassStudents(classId)
    students.value = Array.isArray(list) ? list : []
  } catch (_) { students.value = [] }
}

function onClassChange(e) {
  selectedClassId.value = classOptions.value[e.detail.value]?.id || null
  if (selectedClassId.value) loadStudents(selectedClassId.value)
  else students.value = []
  loadCases()
}

function onStatusChange(e) {
  selectedStatus.value = statusOptions[e.detail.value]?.value || null
  loadCases()
}

function openDetail(id) { uni.navigateTo({ url: `/subTeacher/caseDetail/index?id=${id}` }) }

function openStudentCases(student) {
  const matched = rows.value.filter(c => c.student_id === student.id)
  if (matched.length === 1) openDetail(matched[0].id)
  else if (matched.length > 1) rows.value = matched
  else uni.showToast({ title: '该学生暂无档案', icon: 'none' })
}

onShow(() => { if (guardRole()) { loadClasses(); loadCases() } })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.filters { display: flex; gap: 12rpx; }
.filter-btn {
  flex: 1;
  display: flex; align-items: center; gap: 8rpx;
  background: #fff;
  border: 2rpx solid #E8E6F0;
  border-radius: 14rpx;
  padding: 18rpx 16rpx;
}
.filter-icon { font-size: 24rpx; }
.filter-text { font-size: 26rpx; color: #1A1636; flex: 1; }
.filter-arrow { font-size: 24rpx; color: #B8B0F6; }

.card {
  background: #fff;
  border-radius: 18rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(107,92,231,0.05);
}
.card-title { font-size: 24rpx; font-weight: 600; color: #8E8B9E; display: block; margin-bottom: 12rpx; }

.student-row { display: flex; align-items: center; gap: 16rpx; padding: 14rpx 0; }
.student-row.has-border { border-top: 2rpx solid #F0EFFC; }
.student-avatar {
  width: 60rpx; height: 60rpx;
  background: linear-gradient(135deg, #6B5CE7, #8B78F0);
  border-radius: 16rpx;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 24rpx; font-weight: 700;
}
.student-info { flex: 1; }
.student-name { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.student-meta { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 2rpx; }
.arrow { font-size: 32rpx; color: #B8B0F6; }

.case-row { display: flex; justify-content: space-between; align-items: center; padding: 14rpx 0; gap: 12rpx; }
.case-row.has-border { border-top: 2rpx solid #F0EFFC; }
.case-info { flex: 1; }
.case-name { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.case-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
</style>
