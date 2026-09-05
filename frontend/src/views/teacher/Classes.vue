<template>
  <div class="page classes-manage-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">班级与教学组织</h1>
        <p class="header-desc">配置各学段年级教学班级、班型属性及学生名册归属。</p>
      </div>
      <el-button type="primary" @click="openDialog">
        <el-icon><Plus /></el-icon>新建班级
      </el-button>
    </div>

    <div class="table-card">
      <el-table :data="classes" v-loading="loading" empty-text="暂无班级数据" style="width: 100%">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column prop="name" label="班级名称" min-width="160">
          <template #default="{ row }">
            <strong class="class-name-text">{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="学年" width="220">
          <template #default="{ row }">
            <div class="school-year-cell"><strong>{{ row.school_year }}</strong><span>{{ row.school_year_starts_on }} 至 {{ row.school_year_ends_on || '—' }}</span></div>
          </template>
        </el-table-column>
        <el-table-column prop="education_stage" label="学段" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.education_stage }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="grade" label="年级" width="100" />
        <el-table-column label="班型" width="160">
          <template #default="{ row }">
            <span>{{ row.class_type }}</span>
            <span v-if="row.short_term_type" class="sub-type-badge">（{{ row.short_term_type }}）</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/teacher/classes/${row.id}/students`)">
              学生名册
            </el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑班级' : '新建班级'" width="460px">
      <el-form :model="form" label-position="top">
        <el-form-item label="学年">
          <el-select v-model="form.school_year" placeholder="选择学年" style="width: 100%" @change="onSchoolYearChange"><el-option v-for="year in schoolYears" :key="year" :label="`${year}学年`" :value="year" /></el-select>
        </el-form-item>
        <el-form-item label="学年开始日期">
          <el-date-picker v-model="form.school_year_starts_on" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" style="width: 100%" />
          <span class="form-help">学生总案的阶段任务时间轴将从该日期开始计算。</span>
        </el-form-item>
        <el-form-item label="学年结束日期">
          <el-date-picker v-model="form.school_year_ends_on" type="date" value-format="YYYY-MM-DD" placeholder="选择结束日期" style="width: 100%" />
          <span class="form-help">结束时间需晚于开始时间，默认为次年07-31。</span>
        </el-form-item>
        <el-form-item label="班级名称">
          <el-input v-model="form.name" placeholder="如：高三1班" />
        </el-form-item>
        <el-form-item label="学段">
          <el-radio-group v-model="form.education_stage" @change="onStageChange">
            <el-radio-button value="初中">初中</el-radio-button>
            <el-radio-button value="高中">高中</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年级">
          <el-select v-model="form.grade" placeholder="选择年级" style="width: 100%"><el-option v-for="grade in availableGrades" :key="grade" :label="grade" :value="grade" /></el-select>
        </el-form-item>
        <el-form-item label="班型">
          <el-select v-model="form.class_type" placeholder="选择班型" style="width: 100%" @change="onClassTypeChange">
            <el-option v-for="type in availableClassTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.class_type === '短期班'" label="短期班类型">
          <el-radio-group v-model="form.short_term_type">
            <el-radio-button value="暑假班">暑假班</el-radio-button>
            <el-radio-button value="寒假班">寒假班</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createClass, deleteClass, listClasses, updateClass } from '../../api/classes'

const classes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const currentSchoolYear = () => {
  const today = new Date()
  const start = today.getMonth() >= 6 ? today.getFullYear() : today.getFullYear() - 1
  return `${start}-${start + 1}`
}
const defaultStartDate = (schoolYear) => `${Number.parseInt(schoolYear, 10)}-08-01`
const defaultEndDate = (schoolYear) => {
  const parts = String(schoolYear).split('-')
  const endYear = Number.parseInt(parts[1], 10) || Number.parseInt(parts[0], 10) + 1
  return `${endYear}-07-31`
}
const initialSchoolYear = currentSchoolYear()
const form = reactive({ name: '', education_stage: '高中', grade: '高三', class_type: '全年班', short_term_type: null, school_year: initialSchoolYear, school_year_starts_on: defaultStartDate(initialSchoolYear), school_year_ends_on: defaultEndDate(initialSchoolYear) })
const gradesByStage = { 初中: ['初一', '初二', '初三'], 高中: ['高一', '高二', '高三', '复读'] }
const availableGrades = computed(() => gradesByStage[form.education_stage])
const availableClassTypes = computed(() => form.education_stage === '高中'
  ? ['短期班', '全年班', '集训班', '1V1']
  : ['短期班', '全年班', '1V1'])
const schoolYears = Array.from({ length: 81 }, (_, i) => {
  const start = 2020 + i
  return `${start}-${start + 1}`
})

function onStageChange() {
  form.grade = gradesByStage[form.education_stage][0]
  // 集训班只属于高中；切换到初中时自动回落到全年班。
  if (form.education_stage === '初中' && form.class_type === '集训班') form.class_type = '全年班'
}

function onClassTypeChange() {
  form.short_term_type = form.class_type === '短期班' ? '暑假班' : null
}

function onSchoolYearChange(value) {
  form.school_year_starts_on = defaultStartDate(value)
  form.school_year_ends_on = defaultEndDate(value)
}

async function load() {
  loading.value = true
  try {
    classes.value = await listClasses()
  } finally {
    loading.value = false
  }
}

function openDialog() {
  editingId.value = null
  form.name = ''
  form.education_stage = '高中'
  form.grade = '高三'
  form.class_type = '全年班'
  form.short_term_type = null
  form.school_year = currentSchoolYear()
  form.school_year_starts_on = defaultStartDate(form.school_year)
  form.school_year_ends_on = defaultEndDate(form.school_year)
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    education_stage: row.education_stage,
    grade: row.grade,
    class_type: row.class_type,
    short_term_type: row.short_term_type,
    school_year: row.school_year || '未设置',
    school_year_starts_on: row.school_year_starts_on || defaultStartDate(row.school_year),
    school_year_ends_on: row.school_year_ends_on || defaultEndDate(row.school_year),
  })
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name || !form.education_stage || !form.grade || !form.class_type || !form.school_year || !form.school_year_starts_on || !form.school_year_ends_on) {
    ElMessage.warning('请完整填写学年、起止日期、班级名称、学段、年级和班型')
    return
  }
  if (form.school_year_ends_on <= form.school_year_starts_on) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return
  }
  if (form.class_type === '短期班' && !form.short_term_type) {
    ElMessage.warning('请选择暑假班或寒假班')
    return
  }
  if (editingId.value) await updateClass(editingId.value, { ...form })
  else await createClass({ ...form })
  ElMessage.success(editingId.value ? '班级信息已更新' : '班级已创建')
  dialogVisible.value = false
  load()
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除班级「${row.name}」？仅未关联档案、作业或反馈数据的班级可以删除。`, '删除班级', { type: 'warning', confirmButtonText: '确认删除' })
  } catch { return }
  await deleteClass(row.id)
  ElMessage.success('班级已删除，学生账号不会被删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.classes-manage-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.header-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
}

.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
  padding: 16px 18px;
}

.class-name-text {
  color: var(--ink);
  font-weight: 600;
}

.sub-type-badge {
  color: #64748b;
  font-size: 12px;
}

.school-year-cell { display: grid; gap: 2px; }
.school-year-cell strong { color: var(--ink); font-size: 13px; font-weight: 650; }
.school-year-cell span, .form-help { color: var(--ink-muted); font-size: 11px; }
.form-help { display: block; margin-top: 6px; line-height: 1.5; }
</style>
