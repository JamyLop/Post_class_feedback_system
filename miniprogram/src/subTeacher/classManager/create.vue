<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">新建班级</text>
      <text class="p">创建一个新的班级</text>
    </view>

    <view class="card">
      <text class="card-title">班级信息 · 由德育主任新建并分配班主任</text>
      <view class="form">
        <view class="field">
          <text class="field-label">分配班主任 <text class="required">*</text></text>
          <picker :range="teacherOptions" range-key="label" :value="teacherIndex" @change="onTeacherChange">
            <view class="input picker-input">
              <text>{{ teacherLabel }}</text>
              <text class="picker-arrow">⌄</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">班级名称 <text class="required">*</text></text>
          <input v-model="form.name" placeholder="如：高三(1)班" class="input" />
        </view>
        <view class="field">
          <text class="field-label">学段 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="s in stageOptions"
              :key="s"
              class="radio-item"
              :class="{ active: form.education_stage === s }"
              @click="form.education_stage = s; form.grade = ''"
            >
              <text class="radio-label">{{ s }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">年级 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="g in gradeOptions"
              :key="g"
              class="radio-item"
              :class="{ active: form.grade === g }"
              @click="form.grade = g"
            >
              <text class="radio-label">{{ g }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">班级类型 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="t in typeOptions"
              :key="t"
              class="radio-item"
              :class="{ active: form.class_type === t }"
              @click="form.class_type = t"
            >
              <text class="radio-label">{{ t }}</text>
            </view>
          </view>
        </view>
        <view class="field" v-if="form.class_type === '短期班'">
          <text class="field-label">短期类型 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="st in shortTypeOptions"
              :key="st"
              class="radio-item"
              :class="{ active: form.short_term_type === st }"
              @click="form.short_term_type = st"
            >
              <text class="radio-label">{{ st }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">学年 <text class="required">*</text></text>
          <picker :range="schoolYearOptions" :value="schoolYearIndex" @change="onSchoolYearChange">
            <view class="input picker-input">
              <text>{{ form.school_year || '请选择学年' }}</text>
              <text class="picker-arrow">⌄</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">学年开始日期 <text class="required">*</text></text>
          <picker mode="date" :value="form.school_year_starts_on" @change="onStartsOnChange">
            <view class="input picker-input">
              <text>{{ form.school_year_starts_on || '请选择开始日期' }}</text>
              <text class="picker-arrow">⌄</text>
            </view>
          </picker>
          <text class="form-help">学生总案的阶段任务时间轴将从该日期开始计算。</text>
        </view>
        <view class="field">
          <text class="field-label">学年结束日期 <text class="required">*</text></text>
          <picker mode="date" :value="form.school_year_ends_on" @change="onEndsOnChange">
            <view class="input picker-input">
              <text>{{ form.school_year_ends_on || '请选择结束日期' }}</text>
              <text class="picker-arrow">⌄</text>
            </view>
          </picker>
          <text class="form-help">结束时间需晚于开始时间，默认为次年07-31。</text>
        </view>
      </view>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" :disabled="submitting" @click="handleSubmit">
        {{ submitting ? '创建中...' : '创建班级' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { createClass, listUsers } from '../../api/classes'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const submitting = ref(false)

const stageOptions = ['初中', '高中']
const gradeMap = {
  '初中': ['初一', '初二', '初三'],
  '高中': ['高一', '高二', '高三'],
}
const typeOptions = ['全年班', '短期班', '集训班', '1V1']
const shortTypeOptions = ['暑假班', '寒假班']

function currentSchoolYear() {
  const today = new Date()
  const start = today.getMonth() >= 6 ? today.getFullYear() : today.getFullYear() - 1
  return `${start}-${start + 1}`
}
function defaultStartDate(schoolYear) {
  const startYear = Number.parseInt(String(schoolYear).split('-')[0], 10)
  return `${Number.isNaN(startYear) ? new Date().getFullYear() : startYear}-08-01`
}
function defaultEndDate(schoolYear) {
  const parts = String(schoolYear).split('-')
  const endYear = Number.parseInt(parts[1], 10) || Number.parseInt(parts[0], 10) + 1
  return `${endYear}-07-31`
}
const initialSchoolYear = currentSchoolYear()

const form = reactive({
  name: '',
  education_stage: '高中',
  grade: '高三',
  class_type: '全年班',
  short_term_type: null,
  school_year: initialSchoolYear,
  school_year_starts_on: defaultStartDate(initialSchoolYear),
  school_year_ends_on: defaultEndDate(initialSchoolYear),
  teacher_id: null,
})

const teacherOptions = ref([{ id: null, label: '请选择班主任' }])
const teacherIndex = computed(() => {
  const idx = teacherOptions.value.findIndex((t) => t.id === form.teacher_id)
  return idx >= 0 ? idx : 0
})
const teacherLabel = computed(() => teacherOptions.value[teacherIndex.value]?.label || '请选择班主任')
function onTeacherChange(e) {
  form.teacher_id = teacherOptions.value[Number(e.detail.value)]?.id || null
}

onMounted(async () => {
  // 德育主任新建时需选择班主任
  try {
    const teachers = await listUsers('teacher', '').catch(() => [])
    teacherOptions.value = [
      { id: null, label: '请选择班主任' },
      ...(teachers || []).map((u) => ({ id: u.id, label: `${u.name}（${u.username}）` })),
    ]
  } catch (_) {}
})

const schoolYearOptions = Array.from({ length: 81 }, (_, i) => {
  const start = 2020 + i
  return `${start}-${start + 1}`
})
const schoolYearIndex = computed(() => Math.max(0, schoolYearOptions.indexOf(form.school_year)))

function onSchoolYearChange(e) {
  const year = schoolYearOptions[Number(e.detail.value)]
  if (!year) return
  form.school_year = year
  form.school_year_starts_on = defaultStartDate(year)
  form.school_year_ends_on = defaultEndDate(year)
}
function onStartsOnChange(e) {
  form.school_year_starts_on = e.detail.value
}
function onEndsOnChange(e) {
  form.school_year_ends_on = e.detail.value
}

const gradeOptions = computed(() => gradeMap[form.education_stage] || [])

function validate() {
  if (!form.teacher_id) {
    uni.showToast({ title: '请选择分配的班主任', icon: 'none' })
    return false
  }
  if (!form.name.trim()) {
    uni.showToast({ title: '请输入班级名称', icon: 'none' })
    return false
  }
  if (!form.education_stage) {
    uni.showToast({ title: '请选择学段', icon: 'none' })
    return false
  }
  if (!form.grade) {
    uni.showToast({ title: '请选择年级', icon: 'none' })
    return false
  }
  if (!form.class_type) {
    uni.showToast({ title: '请选择班级类型', icon: 'none' })
    return false
  }
  if (form.class_type === '短期班' && !form.short_term_type) {
    uni.showToast({ title: '请选择短期类型', icon: 'none' })
    return false
  }
  if (!form.school_year || !form.school_year_starts_on || !form.school_year_ends_on) {
    uni.showToast({ title: '请完整填写学年与起止日期', icon: 'none' })
    return false
  }
  if (form.school_year_ends_on <= form.school_year_starts_on) {
    uni.showToast({ title: '结束时间必须晚于开始时间', icon: 'none' })
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    await createClass({
      name: form.name.trim(),
      education_stage: form.education_stage,
      grade: form.grade,
      class_type: form.class_type,
      short_term_type: form.short_term_type,
      school_year: form.school_year,
      school_year_starts_on: form.school_year_starts_on,
      school_year_ends_on: form.school_year_ends_on,
      teacher_id: form.teacher_id,
    })
    uni.showToast({ title: '创建成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-bottom: 14rpx; }

.form { display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 8rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: var(--mp-body); }
.required { color: #A33E39; }
.input {
  border: 1rpx solid #C6D0DE; border-radius: 8rpx;
  padding: 18rpx 22rpx; font-size: 28rpx; background: #fff;
}
.picker-input { display: flex; align-items: center; justify-content: space-between; }
.picker-arrow { color: var(--mp-muted); }
.form-help { font-size: 22rpx; color: var(--mp-muted); line-height: 1.5; }

.radio-group { display: flex; flex-wrap: wrap; gap: 12rpx; }
.radio-item {
  padding: 14rpx 24rpx; border-radius: 8rpx;
  border: 1rpx solid #C6D0DE; background: #fff;
}
.radio-item.active { border-color: var(--mp-primary); background: var(--mp-soft); }
.radio-label { font-size: 26rpx; color: var(--mp-body); }
.radio-item.active .radio-label { color: var(--mp-primary); font-weight: 600; }

.submit-bar {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid var(--mp-line);
}
.btn-submit {
  background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none;
}
.btn-submit::after { border: none; }
</style>
