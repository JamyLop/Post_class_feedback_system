<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head"><text class="h1">{{ checkinMode ? '选择打卡档案' : '学生档案' }}</text><text class="p">{{ checkinMode ? '先选择学生，再记录任务的执行情况' : '按班级与状态查阅学生的学业发展方案' }}</text></view>
    <view class="filter-panel">
      <input v-model="keyword" class="search-input" placeholder="搜索学生姓名" confirm-type="search" />
      <view class="filters">
        <picker :range="classOptions" range-key="name" :value="classIndex" @change="onClassChange"><view class="filter-btn"><text class="filter-text">{{ selectedClassName }}</text><text class="filter-arrow">⌄</text></view></picker>
        <picker :range="statusOptions" range-key="label" :value="statusIndex" @change="onStatusChange"><view class="filter-btn"><text class="filter-text">{{ selectedStatusLabel }}</text><text class="filter-arrow">⌄</text></view></picker>
      </view>
    </view>
    <LoadState :loading="loading" :error="error" @retry="refresh" />
    <template v-if="!loading && !error">
      <view class="result-heading"><text>档案 {{ visibleRows.length }} 份</text><button v-if="keyword || selectedClassId || selectedStatus" class="reset" @click="resetFilters">重置筛选</button></view>
      <view v-if="visibleRows.length" class="case-list">
        <view v-for="c in visibleRows" :key="c.id" class="case-row" hover-class="tap-active" @click="openDetail(c.id)">
          <view class="case-top"><text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text><CaseStatusTag :status="c.status" /></view>
          <text class="case-meta">{{ c.class_name || '未分班' }} · 第 {{ c.version }} 版</text>
          <view class="case-bottom"><text>{{ (c.updated_at || '').slice(0,10) || '暂无更新日期' }} 更新</text><text class="detail-link">{{ checkinMode ? '选择任务' : '查看档案' }} ›</text></view>
        </view>
      </view>
      <EmptyState v-else :title="keyword || selectedStatus ? '没有符合条件的档案' : '暂无档案'" :desc="keyword || selectedStatus ? '尝试更换姓名或状态，也可重置筛选。' : '班主任建立学生档案后，可在这里查看。'" />
      <view v-if="selectedClassId && students.length && !checkinMode" class="roster">
        <button class="roster-toggle" @click="showStudents = !showStudents">班级学生 {{ students.length }} 人 <text>{{ showStudents ? '收起 −' : '展开 +' }}</text></button>
        <view v-if="showStudents">
          <view v-for="s in visibleStudents" :key="s.id" class="student-row" @click="openStudentCases(s)"><text>{{ s.name }}</text><text class="detail-link">查看档案 ›</text></view>
        </view>
      </view>
    </template>
  </view>
</template>
<script setup>
import { ref, computed } from 'vue'
import { onShow, onLoad } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases, listClasses, listClassStudents } from '../../api/studentCases'
import { CASE_STATUS_LABELS } from '../../utils/constants'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'
import LoadState from '../../components/LoadState.vue'
const auth = useAuthStore()
const loading = ref(false), error = ref(''), rows = ref([]), classes = ref([]), students = ref([])
const selectedClassId = ref(null), selectedStatus = ref(null), keyword = ref(''), showStudents = ref(false), checkinMode = ref(false)
const classOptions = computed(() => [{ id: null, name: '全部班级' }, ...classes.value])
const statusOptions = [{ value: null, label: '全部状态' }, ...Object.entries(CASE_STATUS_LABELS).map(([value, label]) => ({ value, label }))]
const classIndex = computed(() => Math.max(0, classOptions.value.findIndex(c => c.id === selectedClassId.value)))
const statusIndex = computed(() => Math.max(0, statusOptions.findIndex(s => s.value === selectedStatus.value)))
const selectedClassName = computed(() => classOptions.value[classIndex.value].name)
const selectedStatusLabel = computed(() => statusOptions[statusIndex.value].label)
const visibleRows = computed(() => rows.value.filter(c => !keyword.value.trim() || (c.student_name || '').includes(keyword.value.trim())))
const visibleStudents = computed(() => students.value.filter(s => !keyword.value.trim() || (s.name || '').includes(keyword.value.trim())))
let requestVersion = 0
function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'deyu_director', 'admin', 'subject_teacher'].includes(auth.role)) { uni.reLaunch({ url: '/pages/index/index' }); return false }
  // 任课老师可读所带班级档案，不能使用班主任的任务打卡入口。
  if (checkinMode.value && auth.role !== 'teacher') checkinMode.value = false
  return true
}
async function refresh() {
  const version = ++requestVersion
  loading.value = true; error.value = ''
  const params = {}
  if (selectedClassId.value) params.class_id = selectedClassId.value
  if (selectedStatus.value) params.status = selectedStatus.value
  try {
    const [list, roster, classList] = await Promise.all([listStudentCases(params), selectedClassId.value && !checkinMode.value ? listClassStudents(selectedClassId.value) : Promise.resolve([]), listClasses()])
    // 快速切换筛选时，只允许最后一次请求更新页面。
    if (version !== requestVersion) return
    rows.value = Array.isArray(list) ? list : []
    students.value = Array.isArray(roster) ? roster : []
    classes.value = Array.isArray(classList) ? classList : []
  } catch (_) { if (version === requestVersion) error.value = '暂时无法读取档案，请检查网络后重试。' }
  finally { if (version === requestVersion) loading.value = false }
}
function onClassChange(e) { selectedClassId.value = classOptions.value[Number(e.detail.value)]?.id || null; showStudents.value = false; refresh() }
function onStatusChange(e) { selectedStatus.value = statusOptions[Number(e.detail.value)]?.value || null; refresh() }
function resetFilters() { keyword.value = ''; selectedClassId.value = null; selectedStatus.value = null; showStudents.value = false; refresh() }
function openDetail(id) { uni.navigateTo({ url: checkinMode.value ? `/subTeacher/checkin/index?caseId=${id}` : `/subTeacher/caseDetail/index?id=${id}` }) }
function openStudentCases(student) {
  const matched = rows.value.filter(c => c.student_id === student.id)
  if (matched.length === 1) openDetail(matched[0].id)
  else if (matched.length > 1) { keyword.value = student.name; showStudents.value = false }
  else uni.showToast({ title: '当前筛选下没有该学生档案', icon: 'none' })
}
onLoad(options => { checkinMode.value = options.action === 'checkin' })
onShow(() => { if (guardRole()) refresh() })
</script>
<style scoped>
.page { padding: 28rpx 32rpx calc(40rpx + env(safe-area-inset-bottom)); display: flex; flex-direction: column; gap: 24rpx; }
.head { padding: 8rpx 0; }.h1 { display: block; font-size: 38rpx; font-weight: 600; }.p { display: block; font-size: 25rpx; color: var(--mp-muted); margin-top: 12rpx; }
.filter-panel { padding: 24rpx; background: white; border-radius: 16rpx; }.search-input { height: 84rpx; padding: 16rpx 20rpx; background: #F3F5F8; border-radius: 8rpx; font-size: 27rpx; border: 1rpx solid var(--mp-line); }.filters { display: flex; gap: 16rpx; margin-top: 18rpx; }.filter-btn { display: flex; align-items: center; gap: 12rpx; min-height: 80rpx; padding: 14rpx 16rpx; border: 1rpx solid #C6D0DE; border-radius: 8rpx; }.filter-text { flex: 1; font-size: 25rpx; color: var(--mp-body); }.filter-arrow { color: var(--mp-muted); }
.result-heading { display: flex; justify-content: space-between; align-items: center; color: var(--mp-muted); font-size: 24rpx; min-height: 56rpx; }.reset { font-size: 24rpx; color: var(--mp-primary); background: transparent; padding: 12rpx 0; }
.case-list { background: white; border-radius: 16rpx; padding: 0 28rpx; }.case-row { padding: 28rpx 0; }.case-row + .case-row { border-top: 1rpx solid var(--mp-line); }.case-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12rpx; }.case-name { font-size: 31rpx; font-weight: 600; }.case-meta { display: block; font-size: 25rpx; margin-top: 10rpx; color: var(--mp-body); }.case-bottom { display: flex; justify-content: space-between; gap: 16rpx; margin-top: 20rpx; font-size: 23rpx; color: var(--mp-muted); }.detail-link { color: var(--mp-primary); font-size: 24rpx; }
.roster { background: white; border-radius: 16rpx; padding: 0 24rpx; }.roster-toggle { background: transparent; display: flex; justify-content: space-between; padding: 24rpx 0; font-size: 26rpx; color: var(--mp-body); }.student-row { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; border-top: 1rpx solid var(--mp-line); padding: 22rpx 0; font-size: 27rpx; }
</style>
