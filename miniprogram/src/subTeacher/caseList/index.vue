<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head"><text class="h1">{{ checkinMode ? '选择打卡档案' : '学生档案' }}</text><text class="p">{{ checkinMode ? '先选择学生，再记录任务的执行情况' : '按班级与状态查阅学生的学业发展方案' }}</text></view>
    <view v-if="!checkinMode && auth.role === 'teacher'" class="action-bar">
      <button class="btn-primary" @click="openCreate">新建档案</button>
    </view>
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
    <view v-if="createVisible" class="modal-mask" @click.self="createVisible=false">
      <view class="modal">
        <view class="modal-header">
          <text class="modal-title">新建学生总案</text>
          <text class="modal-close" @click="createVisible=false">✕</text>
        </view>
        <view class="form">
          <view class="field">
            <text class="label">学年 <text class="required">*</text></text>
            <picker :range="cycleOptions" range-key="label" :value="cycleIndex" @change="onCreateCycleChange">
              <view class="picker-input"><text>{{ createCycleLabel }}</text><text class="picker-arrow">⌄</text></view>
            </picker>
          </view>
          <view class="field">
            <text class="label">班级 <text class="required">*</text></text>
            <picker :range="createClassOptions" range-key="name" :value="createClassIndex" @change="onCreateClassChange">
              <view class="picker-input"><text>{{ createClassName }}</text><text class="picker-arrow">⌄</text></view>
            </picker>
          </view>
          <view class="field">
            <text class="label">学生 <text class="required">*</text></text>
            <picker :range="createStudentOptions" range-key="label" :value="createStudentIndex" @change="onCreateStudentChange">
              <view class="picker-input"><text>{{ createStudentLabel }}</text><text class="picker-arrow">⌄</text></view>
            </picker>
            <text v-if="!createStudentOptions.length" class="form-help">该班级暂无可建档学生（可能均已建档），请先在班级管理新建学生。</text>
          </view>
          <view class="field">
            <text class="label">家长评价</text>
            <textarea v-model="createForm.parent_evaluation" placeholder="记录家长对学生的评价、关注点或家校协同建议" class="textarea" />
          </view>
          <view class="field">
            <text class="label">主要需求</text>
            <textarea v-model="createForm.primary_needs" placeholder="例如：学生主要需求、期望支持方向或家校配合事项" class="textarea" />
          </view>
          <view class="field">
            <text class="label">当前状态说明</text>
            <textarea v-model="createForm.current_summary" placeholder="例如：班主任手工建档，待完善教学方案" class="textarea" />
          </view>
        </view>
        <view class="modal-btns">
          <button class="btn-outline" @click="createVisible=false">取消</button>
          <button class="btn-primary" :loading="creating" :disabled="creating" @click="submitCreate">{{ creating ? '创建中...' : '创建并进入档案' }}</button>
        </view>
      </view>
    </view>
  </view>
</template>
<script setup>
import { ref, computed } from 'vue'
import { onShow, onLoad } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases, listClasses, listClassStudents, listCaseCycles, createCaseCycle, createStudentCase, addStudentsToClass, listUsers } from '../../api/studentCases'
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
// ---- 新建档案（对齐网页端 StudentCases.vue） ----
const createVisible = ref(false), creating = ref(false)
const cycles = ref([]), allStudents = ref([]), createRoster = ref([])
const createForm = ref({ cycle_id: null, class_id: null, student_id: null, parent_evaluation: '', primary_needs: '', current_summary: '班主任手工建档，待完善教学方案' })
const schoolYears = Array.from({ length: 81 }, (_, i) => { const s = 2020 + i; return `${s}-${s + 1}` })
const cycleOptions = computed(() => {
  const byYear = new Map((cycles.value || []).map(c => [c.school_year, c]))
  return schoolYears.map(year => {
    const existing = byYear.get(year)
    if (existing) return { id: existing.id, label: `${year}学年`, _virtual: false }
    return { id: year, label: `${year}学年`, _virtual: true }
  })
})
const cycleIndex = computed(() => Math.max(0, cycleOptions.value.findIndex(c => String(c.id) === String(createForm.value.cycle_id))))
const createCycleLabel = computed(() => cycleOptions.value[cycleIndex.value]?.label || '请选择学年')
const createClassOptions = computed(() => classes.value || [])
const createClassIndex = computed(() => Math.max(0, createClassOptions.value.findIndex(c => c.id === createForm.value.class_id)))
const createClassName = computed(() => createClassOptions.value[createClassIndex.value]?.name || (createClassOptions.value.length ? '请选择班级' : '暂无班级，请先创建班级'))
const classRosterIds = computed(() => new Set((createRoster.value || []).map(s => s.id)))
const createStudentOptions = computed(() => {
  const existing = new Set((rows.value || []).filter(c => String(c.cycle_id) === String(resolveCycleIdForFilter())).map(c => c.student_id))
  let pool = (allStudents.value || []).filter(s => !existing.has(s.id))
  if (createForm.value.class_id) pool = pool.filter(s => classRosterIds.value.has(s.id))
  return pool.map(s => ({ id: s.id, label: `${s.name}（${s.username}）${classRosterIds.value.has(s.id) ? '' : ' · 创建时加入班级'}` }))
})
const createStudentIndex = computed(() => Math.max(0, createStudentOptions.value.findIndex(s => s.id === createForm.value.student_id)))
const createStudentLabel = computed(() => createStudentOptions.value[createStudentIndex.value]?.label || (createStudentOptions.value.length ? '请选择学生' : '暂无可选学生'))
function resolveCycleIdForFilter() {
  const opt = cycleOptions.value.find(c => String(c.id) === String(createForm.value.cycle_id))
  if (!opt) return createForm.value.cycle_id
  if (opt._virtual) return null
  return opt.id
}
function onCreateCycleChange(e) { createForm.value.cycle_id = cycleOptions.value[Number(e.detail.value)]?.id || null; createForm.value.student_id = null }
async function onCreateClassChange(e) {
  createForm.value.class_id = createClassOptions.value[Number(e.detail.value)]?.id || null
  createForm.value.student_id = null
  if (createForm.value.class_id) {
    try { createRoster.value = await listClassStudents(createForm.value.class_id) } catch (_) { createRoster.value = [] }
  } else createRoster.value = []
}
function onCreateStudentChange(e) { createForm.value.student_id = createStudentOptions.value[Number(e.detail.value)]?.id || null }
async function openCreate() {
  creating.value = true
  try {
    const [cycleList, classList, studentList] = await Promise.all([listCaseCycles().catch(() => []), listClasses().catch(() => []), listUsers({ role: 'student' }).catch(() => [])])
    cycles.value = Array.isArray(cycleList) ? cycleList : []
    classes.value = Array.isArray(classList) ? classList : []
    allStudents.value = Array.isArray(studentList) ? studentList : []
    const activeCycle = cycles.value.find(c => c.is_active) || cycles.value[0]
    const firstClass = classes.value[0]
    const defaultYear = firstClass?.school_year || activeCycle?.school_year || '2026-2027'
    const defaultCycle = cycles.value.find(c => c.school_year === defaultYear)
    Object.assign(createForm.value, { cycle_id: defaultCycle ? defaultCycle.id : defaultYear, class_id: firstClass?.id || null, student_id: null, parent_evaluation: '', primary_needs: '', current_summary: '班主任手工建档，待完善教学方案' })
    if (firstClass) {
      try { createRoster.value = await listClassStudents(firstClass.id) } catch (_) { createRoster.value = [] }
    } else createRoster.value = []
    createVisible.value = true
  } catch (_) { uni.showToast({ title: '加载建档选项失败', icon: 'none' }) }
  finally { creating.value = false }
}
async function submitCreate() {
  if (!createForm.value.cycle_id || !createForm.value.class_id || !createForm.value.student_id) {
    uni.showToast({ title: '请选择学年、班级和学生', icon: 'none' })
    return
  }
  creating.value = true
  try {
    let cycleId = createForm.value.cycle_id
    if (typeof cycleId === 'string' && cycleId.includes('-')) {
      const year = cycleId
      const startYear = Number.parseInt(year.split('-')[0], 10)
      const selectedClass = classes.value.find(c => c.id === createForm.value.class_id)
      const createdCycle = await createCaseCycle({ name: `${year}学年`, school_year: year, starts_on: selectedClass?.school_year_starts_on || `${startYear}-08-01`, ends_on: `${startYear + 1}-06-30` })
      cycles.value.push(createdCycle)
      cycleId = createdCycle.id
    }
    if (!classRosterIds.value.has(createForm.value.student_id)) {
      await addStudentsToClass(createForm.value.class_id, [createForm.value.student_id])
    }
    const created = await createStudentCase({ ...createForm.value, cycle_id: cycleId, owner_teacher_id: auth.user?.id })
    uni.showToast({ title: '学生总案已创建', icon: 'success' })
    createVisible.value = false
    await refresh()
    if (created?.id) openDetail(created.id)
  } catch (_) {}
  finally { creating.value = false }
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
.action-bar { display: flex; gap: 16rpx; }.action-bar .btn-primary { flex: 1; background: var(--mp-primary); color: #fff; border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none; }.action-bar .btn-primary::after { border: none; }
.form { display: flex; flex-direction: column; gap: 16rpx; }.field { display: flex; flex-direction: column; gap: 8rpx; }.label { font-size: 25rpx; font-weight: 600; color: var(--mp-ink); }.required { color: #A33E39; }.picker-input { display: flex; align-items: center; justify-content: space-between; border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 20rpx; font-size: 26rpx; background: #fff; }.picker-arrow { color: var(--mp-muted); }.form-help { font-size: 22rpx; color: var(--mp-muted); line-height: 1.5; }.textarea { border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 16rpx 18rpx; font-size: 26rpx; min-height: 120rpx; background: #fff; }
.modal-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(26,22,54,0.45); display: flex; align-items: flex-end; z-index: 999; }.modal { background: #fff; border-radius: 24rpx 24rpx 0 0; padding: 28rpx; width: 100%; max-height: 86vh; overflow-y: auto; display: flex; flex-direction: column; gap: 16rpx; }.modal-header { display: flex; justify-content: space-between; align-items: center; }.modal-title { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }.modal-close { font-size: 28rpx; color: var(--mp-muted); padding: 8rpx; }.modal-btns { display: flex; gap: 14rpx; margin-top: 8rpx; }.modal-btns button { flex: 1; }.btn-outline { background: #fff; color: var(--mp-primary); border: 1rpx solid #B8C6D8; border-radius: 8rpx; padding: 20rpx 0; font-size: 28rpx; }.btn-outline::after { border: none; }
</style>
