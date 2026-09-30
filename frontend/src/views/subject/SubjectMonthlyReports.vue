<template>
  <section class="page monthly-page">
    <header class="page-head">
      <div>
        <div class="scope-line"><span>任课协同</span><span>月度评定 · 学科评价</span></div>
        <h1>月度评定与学科评价</h1>
        <p>为对应学生填写所带学科的总结、问题、计划；德育由班主任填写。</p>
      </div>
      <el-button type="primary" @click="openCreate">填写本月评定</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </header>

    <section class="filter-surface">
      <div class="filters">
        <el-select v-model="filters.class_id" placeholder="选择班级" clearable style="width: 180px" @change="onFilterClassChange">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-date-picker v-model="filters.month_label" type="month" placeholder="月份" value-format="YYYY-MM" style="width: 160px" @change="load" />
        <el-input v-model="keyword" placeholder="搜索学生" clearable style="width: 180px" :prefix-icon="Search" />
      </div>
    </section>

    <section class="list-surface">
      <el-table v-loading="loading" :data="filteredRows" empty-text="暂无所带班级的月度评定">
        <el-table-column prop="month_label" label="月份" width="110" />
        <el-table-column label="学生 / 班级" min-width="150">
          <template #default="{ row }"><strong>{{ row.student_name || `学生#${row.student_id}` }}</strong><div class="secondary">{{ row.class_name }}</div></template>
        </el-table-column>
        <el-table-column label="德育评定（班主任）" min-width="220" show-overflow-tooltip>
          <template #default="{ row }"><span class="final-content">{{ row.final_content || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="学科评价" min-width="300">
          <template #default="{ row }"><MonthlyReportEvaluations :report="row" @saved="updated => Object.assign(row, updated)" /></template>
        </el-table-column>
      </el-table>
    </section>
    <el-dialog v-model="creating" title="填写学科月度评定" width="min(560px, 92vw)">
      <el-form label-position="top">
        <el-form-item label="班级"><el-select v-model="form.class_id" @change="changeClass"><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="学生"><el-select v-model="form.student_id" filterable><el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="月份"><el-date-picker v-model="form.month_label" type="month" value-format="YYYY-MM" /></el-form-item>
        <MonthlyReviewForm v-model="form.final_content" :limit="600" :disabled="saving" />
      </el-form>
      <template #footer><el-button :disabled="saving" @click="creating = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitCreate">保存学科评定</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import MonthlyReportEvaluations from '../../components/MonthlyReportEvaluations.vue'
import MonthlyReviewForm from '../../components/MonthlyReviewForm.vue'
import { completeReview } from '../../utils/monthlyReview'
import { ElMessage } from 'element-plus'
import { listClasses, listStudents } from '../../api/classes'
import { createMonthlyReport, listMonthlyReports, saveMonthlyEvaluation } from '../../api/monthlyReports'

const creating = ref(false)
const saving = ref(false)
const students = ref([])
const form = ref({ class_id: null, student_id: null, month_label: '', final_content: '' })
async function changeClass() {
  form.value.student_id = null
  students.value = form.value.class_id ? await listStudents(form.value.class_id) : []
}
async function openCreate() {
  const now = new Date()
  form.value = { class_id: filters.value.class_id || classes.value[0]?.id, student_id: null, month_label: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`, final_content: '' }
  await changeClass()
  creating.value = true
}
async function submitCreate() {
  if (saving.value) return
  if (!form.value.student_id || !form.value.month_label || !completeReview(form.value.final_content)) {
    ElMessage.warning('请选择学生、月份并填写总结、问题、计划')
    return
  }
  saving.value = true
  try {
    const existing = (await listMonthlyReports({ class_id: form.value.class_id, student_id: form.value.student_id, month_label: form.value.month_label }))[0]
    if (existing) {
      await saveMonthlyEvaluation(existing.id, { content: form.value.final_content })
    } else {
      await createMonthlyReport(form.value)
    }
    creating.value = false
    ElMessage.success('学科评定已保存')
    await load()
  } finally { saving.value = false }
}
const classes = ref([])
const rows = ref([])
const loading = ref(false)
const keyword = ref('')
const filters = ref({ class_id: null, month_label: '' })

const statusText = (s) => ({ generating: '待填写', generated: '待发布', published: '已发布', failed: '待补充' }[s] || s)
const statusType = (s) => ({ generated: 'warning', published: 'success', failed: 'danger' }[s] || 'info')

const filteredRows = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter(r => `${r.student_name || ''}${r.class_name || ''}`.toLowerCase().includes(q))
})

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.class_id) params.class_id = filters.value.class_id
    if (filters.value.month_label) params.month_label = filters.value.month_label
    rows.value = await listMonthlyReports(params)
  } finally {
    loading.value = false
  }
}

async function onFilterClassChange() {
  await load()
}

onMounted(async () => {
  classes.value = await listClasses().catch(() => [])
  if (classes.value.length === 1) filters.value.class_id = classes.value[0].id
  await load()
})
</script>

<style scoped>
.monthly-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.scope-line { display: flex; gap: 8px; margin-bottom: 8px; }
.scope-line span { font-size: 11px; font-weight: 600; color: #0f766e; background: #ccfbf1; border: 1px solid #99f6e4; padding: 2px 8px; border-radius: 6px; }
.scope-line span + span { color: #64748b; background: #ffffff; border-color: #e2e8f0; }
.page-head h1 { margin: 0 0 6px; font-size: var(--font-size-page-title); font-weight: var(--font-weight-heading); color: var(--ink); letter-spacing: normal; }
.page-head p { margin: 0; color: #64748b; font-size: 13.5px; max-width: 68ch; line-height: 1.5; }
.filter-surface, .list-surface { background: #ffffff; border: 1px solid #e2e8f0; border-radius: var(--radius); box-shadow: none; padding: 16px 18px; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.secondary { color: var(--ink-muted); font-size: 12px; line-height: 1.6; }
.final-content { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; white-space: pre-wrap; line-height: 1.6; }
@media (max-width: 760px) { .page-head { flex-direction: column; } }
</style>
