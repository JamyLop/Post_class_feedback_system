<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">新建学生档案</text>
      <text class="p">只需选择您关联的学生，所属班级自动带出；未分班学生也可直接建档</text>
    </view>

    <view class="card">
      <view class="field">
        <text class="field-label">学年</text>
        <picker :range="cycleLabels" :value="cycleIndex" @change="onCycleChange">
          <view class="input picker-input">
            <text>{{ cycleLabels[cycleIndex] || '请选择' }}</text>
            <text class="picker-arrow">⌄</text>
          </view>
        </picker>
      </view>
      <view class="field">
        <text class="field-label">学生</text>
        <picker :range="studentLabels" :value="studentIndex" @change="onStudentChange">
          <view class="input picker-input">
            <text>{{ studentLabels[studentIndex] || '请选择尚未建档的学生' }}</text>
            <text class="picker-arrow">⌄</text>
          </view>
        </picker>
      </view>
      <view v-if="selectedClassLabel" class="class-tag">
        <text class="class-tag-text">所属班级：{{ selectedClassLabel }}</text>
      </view>
      <view class="field">
        <text class="field-label">家长评价</text>
        <textarea v-model="form.parent_evaluation" placeholder="记录家长对学生的评价、关注点或家校协同建议" class="textarea" auto-height />
      </view>
      <view class="field">
        <text class="field-label">主要需求</text>
        <textarea v-model="form.primary_needs" placeholder="例如：学生主要需求、期望支持方向或家校配合事项" class="textarea" auto-height />
      </view>
      <view class="field">
        <text class="field-label">当前状态说明</text>
        <textarea v-model="form.current_summary" placeholder="例如：咨询老师建档，待完善入学评定" class="textarea" auto-height />
      </view>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" :disabled="submitting" @click="handleSubmit">
        {{ submitting ? '创建中...' : '创建并进入档案' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { currentSchoolYear } from '../../utils/schoolYear'
import {
  listClasses, listClassStudents,
  listCaseCycles, createCaseCycle, createStudentCase, listStudentCases, listUsers,
} from '../../api/studentCases'

const auth = useAuthStore()
const submitting = ref(false)
const classes = ref([])
const cycles = ref([])
const allStudents = ref([])
const existingCases = ref([])
const form = ref({
  cycle_id: null, student_id: null,
  parent_evaluation: '', primary_needs: '', current_summary: '咨询老师建档，待完善入学评定',
})

const schoolYears = Array.from({ length: 11 }, (_, i) => {
  const start = 2022 + i
  return `${start}-${start + 1}`
})
const cycleOptions = computed(() => {
  const byYear = new Map(cycles.value.map((c) => [c.school_year, c]))
  return schoolYears.map((year) => {
    const existing = byYear.get(year)
    if (existing) return existing
    return { id: year, school_year: year, name: `${year}学年`, _virtual: true }
  })
})
const cycleLabels = computed(() => cycleOptions.value.map((c) => `${c.school_year}学年`))
const cycleIndex = computed(() => Math.max(0, cycleOptions.value.findIndex((c) => c.id === form.value.cycle_id)))

const availableStudents = computed(() => {
  const existing = new Set(existingCases.value.filter((item) => item.cycle_id === form.value.cycle_id).map((item) => item.student_id))
  return allStudents.value.filter((item) => !existing.has(item.id))
})
const studentLabels = computed(() => availableStudents.value.map((s) =>
  s.class_id ? `${s.name}（${s.class_name}·${s.username}）` : `${s.name}（未分班·${s.username}）`,
))
const studentIndex = computed(() => Math.max(0, availableStudents.value.findIndex((s) => s.id === form.value.student_id)))
const selectedStudent = computed(() => availableStudents.value.find((s) => s.id === form.value.student_id))
const selectedClassLabel = computed(() => {
  if (!selectedStudent.value) return ''
  return selectedStudent.value.class_id ? selectedStudent.value.class_name : '未分班（入班后自动挂靠）'
})

function onCycleChange(e) {
  form.value.cycle_id = cycleOptions.value[Number(e.detail.value)]?.id ?? null
  form.value.student_id = null
}
function onStudentChange(e) {
  form.value.student_id = availableStudents.value[Number(e.detail.value)]?.id ?? null
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'consultant') {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

onMounted(loadMeta)

async function loadMeta() {
  if (!guardRole()) return
  try {
    const [clsList, cycleList, cases] = await Promise.all([
      listClasses().catch(() => []),
      listCaseCycles().catch(() => []),
      listStudentCases().catch(() => []),
    ])
    classes.value = Array.isArray(clsList) ? clsList : []
    cycles.value = Array.isArray(cycleList) ? cycleList : []
    existingCases.value = Array.isArray(cases) ? cases : []
    const activeCycle = cycles.value.find((item) => item.is_active) || cycles.value[0]
    const defaultYear = activeCycle?.school_year || currentSchoolYear()
    const defaultCycle = cycles.value.find((c) => c.school_year === defaultYear)
    form.value.cycle_id = defaultCycle ? defaultCycle.id : defaultYear
    // 合并所有关联班级名册 + 未分班关联学生（后端 listUsers 已限定仅返回自己关联的学生）
    const [rosters, linkedStudents] = await Promise.all([
      Promise.all(classes.value.map((cls) => listClassStudents(cls.id).catch(() => []))),
      listUsers('student', '').catch(() => []),
    ])
    const linkedIds = new Set((linkedStudents || []).map((item) => item.id))
    const merged = []
    const inRoster = new Set()
    classes.value.forEach((cls, idx) => {
      for (const stu of rosters[idx] || []) {
        if (!linkedIds.has(stu.id)) continue
        inRoster.add(stu.id)
        merged.push({ ...stu, class_id: cls.id, class_name: cls.name })
      }
    })
    for (const stu of linkedStudents || []) {
      if (!inRoster.has(stu.id)) merged.push({ ...stu, class_id: null, class_name: '' })
    }
    allStudents.value = merged
    if (!merged.length) {
      uni.showToast({ title: '没有可建档的学生', icon: 'none' })
    }
  } catch (_) {
    // 错误已统一提示
  }
}

async function handleSubmit() {
  if (!form.value.cycle_id || !form.value.student_id) {
    uni.showToast({ title: '请选择学年和学生', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    let cycleId = form.value.cycle_id
    if (typeof cycleId === 'string' && cycleId.includes('-')) {
      const year = cycleId
      const startYear = Number.parseInt(year.split('-')[0], 10)
      const hit = allStudents.value.find((s) => s.id === form.value.student_id)
      const selectedClass = classes.value.find((item) => item.id === hit?.class_id)
      const createdCycle = await createCaseCycle({
        name: `${year}学年`,
        school_year: year,
        starts_on: selectedClass?.school_year_starts_on || `${startYear}-08-01`,
        ends_on: `${startYear + 1}-06-30`,
      })
      cycles.value.push(createdCycle)
      cycleId = createdCycle.id
    }
    const hit = allStudents.value.find((s) => s.id === form.value.student_id)
    const selectedClass = classes.value.find((item) => item.id === hit?.class_id)
    const created = await createStudentCase({
      cycle_id: cycleId,
      class_id: hit?.class_id ?? null,
      student_id: form.value.student_id,
      owner_teacher_id: selectedClass?.teacher_id || auth.user.id,
      parent_evaluation: form.value.parent_evaluation,
      primary_needs: form.value.primary_needs,
      current_summary: form.value.current_summary,
    })
    uni.showToast({ title: '学生档案已创建', icon: 'success' })
    setTimeout(() => uni.redirectTo({ url: `/subConsultant/caseDetail/index?id=${created.id}` }), 800)
  } catch (_) {
    // 错误已统一提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.card { background: #fff; border-radius: 10rpx; padding: 24rpx; border: 1rpx solid var(--mp-line); display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: var(--mp-body); }
.input { border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 22rpx; font-size: 28rpx; background: #fff; }
.picker-input { display: flex; align-items: center; justify-content: space-between; }
.picker-arrow { color: var(--mp-muted); }
.textarea { border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 22rpx; font-size: 28rpx; background: #fff; min-height: 120rpx; width: 100%; box-sizing: border-box; }
.class-tag { background: var(--mp-soft); border-radius: 8rpx; padding: 14rpx 18rpx; }
.class-tag-text { font-size: 24rpx; color: var(--mp-primary); }
.submit-bar { position: fixed; left: 0; right: 0; bottom: 0; background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom)); border-top: 1rpx solid var(--mp-line); }
.btn-submit { background: var(--mp-primary); color: #fff; border-radius: 8rpx; padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none; }
.btn-submit::after { border: none; }
</style>
