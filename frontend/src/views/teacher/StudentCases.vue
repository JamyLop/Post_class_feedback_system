<template>
  <section class="page cases-page">
    <header class="page-head">
      <div><div class="scope-line"><span>高三试点</span><span>2026-2027备考周期</span></div><h1>学生档案工作台</h1><p>集中查看学生总案、待处理状态、班级执行进度和逾期任务。</p></div>
      <el-button v-if="auth.role === 'teacher'" type="primary" @click="openCreate">新建学生总案</el-button>
    </header>

    <section class="summary-strip" aria-label="学生档案进度摘要">
      <div class="summary-total"><span>学生总案</span><strong>{{ progress.total }}</strong><small>当前高三试点范围</small></div>
      <div class="summary-facts">
        <div><span class="fact-dot amber"></span><p><strong>{{ progress.draft || 0 }}</strong><span>待核对草稿</span></p></div>
        <div><span class="fact-dot blue"></span><p><strong>{{ progress.pending_confirmation || 0 }}</strong><span>待确认</span></p></div>
        <div><span class="fact-dot green"></span><p><strong>{{ progress.executing || 0 }}</strong><span>执行中</span></p></div>
        <div><span class="fact-dot red"></span><p><strong>{{ progress.overdue_tasks || 0 }}</strong><span>逾期任务</span></p></div>
      </div>
    </section>

    <section class="list-surface">
      <div class="list-toolbar">
        <div><h2>学生列表</h2><span>共 {{ filteredRows.length }} 人</span></div>
        <div class="filters">
          <el-select v-model="workFilter" @change="applyWorkFilter"><el-option label="全部档案" value="all" /><el-option label="待处理" value="todo" /><el-option label="执行中" value="executing" /></el-select>
          <el-input v-model="keyword" clearable placeholder="搜索学生或班级" :prefix-icon="Search" />
          <el-select v-model="status" clearable placeholder="全部状态" @change="onStatusChange"><el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" /></el-select>
          <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="filteredRows" empty-text="暂无符合条件的学生总案" class="cases-table" @row-click="openCase">
        <el-table-column label="学生" min-width="150">
          <template #default="{ row }"><div class="student-cell"><span class="student-avatar">{{ row.student_name?.slice(0, 1) }}</span><div><strong>{{ row.student_name }}</strong><small>档案 #{{ row.id }}</small></div></div></template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="150" />
        <el-table-column prop="admission_target" label="升学目标" min-width="260" show-overflow-tooltip />
        <el-table-column prop="current_summary" label="当前进展" min-width="250" show-overflow-tooltip />
        <el-table-column label="方案状态" width="125"><template #default="{ row }"><span class="table-status" :class="`is-${row.status}`"><span></span>{{ statusLabel(row.status) }}</span></template></el-table-column>
        <el-table-column label="版本" width="90"><template #default="{ row }">V{{ row.version }}</template></el-table-column>
        <el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-button link type="primary" @click.stop="openCase(row)">查看档案</el-button></template></el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="createVisible" title="新建学生总案" width="620px" destroy-on-close>
      <el-form label-position="top">
        <div class="create-grid">
          <el-form-item label="备考周期"><el-select v-model="createForm.cycle_id" placeholder="选择高三备考周期"><el-option v-for="item in cycles" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="班级"><el-select v-model="createForm.class_id" placeholder="选择本人负责的高三班级" @change="loadClassStudents"><el-option v-for="item in high3Classes" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        </div>
        <el-form-item label="学生"><el-select v-model="createForm.student_id" filterable placeholder="选择尚未建档的学生"><el-option v-for="item in availableStudents" :key="item.id" :label="`${item.name}（${item.username}）${classStudentIds.has(item.id) ? '' : ' · 创建时加入班级'}`" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="总体问题"><el-input v-model="createForm.overall_problem" type="textarea" :autosize="{ minRows: 3, maxRows: 12 }" placeholder="可暂时留空，建档后继续完整录入" /></el-form-item>
        <el-form-item label="升学目标"><el-input v-model="createForm.admission_target" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" placeholder="可暂时留空" /></el-form-item>
        <el-form-item label="当前状态说明"><el-input v-model="createForm.current_summary" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" placeholder="例如：班主任手工建档，待完善学科方案" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="creating" @click="submitCreate">创建并进入档案</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { addStudents, listClasses, listStudents } from '../../api/classes'
import { createStudentCase, getCaseProgress, listCaseCycles, listStudentCases } from '../../api/studentCases'
import { listUsers } from '../../api/users'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const rows = ref([]), loading = ref(false), status = ref(''), keyword = ref('')
const workFilter = ref('all')
const cycles = ref([]), classes = ref([]), classStudents = ref([]), allStudents = ref([])
const createVisible = ref(false), creating = ref(false)
const createForm = reactive({ cycle_id: null, class_id: null, student_id: null, overall_problem: '', admission_target: '', current_summary: '' })
const progress = ref({ total: 0, draft: 0, pending_confirmation: 0, executing: 0, overdue_tasks: 0 })
const statuses = [['draft', '草稿'], ['pending_confirmation', '待确认'], ['executing', '执行中'], ['pending_review', '待复盘'], ['adjusted', '已调整'], ['archived', '已归档']].map(([value, label]) => ({ value, label }))
const statusLabel = (value) => statuses.find((item) => item.value === value)?.label || value
const filteredRows = computed(() => {
  let result = rows.value
  if (workFilter.value === 'todo') result = result.filter((row) => ['draft', 'pending_confirmation', 'pending_review'].includes(row.status))
  if (workFilter.value === 'executing') result = result.filter((row) => ['executing', 'adjusted'].includes(row.status))
  const query = keyword.value.trim().toLowerCase()
  if (query) result = result.filter((row) => `${row.student_name || ''}${row.class_name || ''}`.toLowerCase().includes(query))
  return result
})
const high3Classes = computed(() => classes.value.filter((item) => item.grade === '高三'))
const classStudentIds = computed(() => new Set(classStudents.value.map((item) => item.id)))
const availableStudents = computed(() => {
  const existing = new Set(rows.value.filter((item) => item.cycle_id === createForm.cycle_id).map((item) => item.student_id))
  return allStudents.value.filter((item) => !existing.has(item.id))
})

function openCase(row) { router.push(`/teacher/student-cases/${row.id}`) }
function applyWorkFilter() {
  status.value = ''
  load()
}
function onStatusChange() { workFilter.value = 'all'; load() }
async function openCreate() {
  creating.value = true
  try {
    [cycles.value, classes.value, allStudents.value] = await Promise.all([listCaseCycles(), listClasses(), listUsers('student')])
    const activeCycle = cycles.value.find((item) => item.is_active) || cycles.value[0]
    const firstClass = high3Classes.value[0]
    Object.assign(createForm, { cycle_id: activeCycle?.id || null, class_id: firstClass?.id || null, student_id: null, overall_problem: '', admission_target: '', current_summary: '班主任手工建档，待完善学科方案' })
    if (firstClass) await loadClassStudents(firstClass.id)
    createVisible.value = true
  } finally { creating.value = false }
}
async function loadClassStudents(classId) {
  createForm.student_id = null
  classStudents.value = classId ? await listStudents(classId) : []
}
async function submitCreate() {
  if (!createForm.cycle_id || !createForm.class_id || !createForm.student_id) {
    ElMessage.warning('请选择备考周期、班级和学生')
    return
  }
  creating.value = true
  try {
    if (!classStudentIds.value.has(createForm.student_id)) {
      await addStudents(createForm.class_id, [createForm.student_id])
    }
    const created = await createStudentCase({ ...createForm, owner_teacher_id: auth.user.id })
    ElMessage.success('学生总案已创建')
    createVisible.value = false
    router.push(`/teacher/student-cases/${created.id}`)
  } finally { creating.value = false }
}
async function load() {
  loading.value = true
  try { const params = status.value ? { status: status.value } : {}; [rows.value, progress.value] = await Promise.all([listStudentCases(params), getCaseProgress()]) } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.cases-page { display: grid; gap: 24px; }.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }.scope-line { display: flex; gap: 8px; margin-bottom: 9px; }.scope-line span { padding: 4px 8px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 6px; font-size: 11px; font-weight: 650; }.scope-line span + span { color: var(--ink-secondary); background: var(--surface-soft); }.page-head h1 { margin: 0; font-size: 29px; letter-spacing: -.025em; }.page-head p { margin: 8px 0 0; color: var(--ink-secondary); font-size: 14px; }.create-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.create-grid :deep(.el-select), :deep(.el-dialog .el-select) { width: 100%; }
.summary-strip { display: flex; align-items: stretch; min-height: 126px; overflow: hidden; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }.summary-total { display: grid; grid-template-columns: auto 1fr; align-content: center; column-gap: 14px; min-width: 230px; padding: 24px 28px; color: #fff; background: var(--brand-strong); }.summary-total span { align-self: end; font-size: 13px; }.summary-total strong { grid-row: span 2; font-size: 42px; line-height: 1; }.summary-total small { color: rgb(255 255 255 / 72%); font-size: 11px; }.summary-facts { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); flex: 1; }.summary-facts > div { display: flex; align-items: center; gap: 12px; padding: 24px; }.summary-facts > div + div { border-left: 1px solid var(--line); }.summary-facts p { display: grid; gap: 4px; margin: 0; }.summary-facts strong { font-size: 25px; }.summary-facts p span { color: var(--ink-muted); font-size: 12px; }.fact-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--ink-muted); }.fact-dot.amber { background: var(--warning); }.fact-dot.blue { background: var(--brand); }.fact-dot.green { background: var(--success); }.fact-dot.red { background: #d84c55; }
.list-surface { overflow: hidden; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }.list-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 20px 22px; border-bottom: 1px solid var(--line); }.list-toolbar > div:first-child { display: flex; align-items: baseline; gap: 10px; }.list-toolbar h2 { margin: 0; font-size: 17px; }.list-toolbar span { color: var(--ink-muted); font-size: 12px; }.filters { display: flex; gap: 10px; }.filters :deep(.el-input) { width: 220px; }.filters :deep(.el-select) { width: 140px; }.cases-table { cursor: pointer; }.cases-table :deep(th.el-table__cell) { height: 46px; color: var(--ink-muted); background: var(--surface-soft); font-size: 12px; font-weight: 650; }.cases-table :deep(td.el-table__cell) { padding: 14px 0; }.student-cell { display: flex; align-items: center; gap: 10px; }.student-avatar { display: grid; place-items: center; width: 34px; height: 34px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 9px; font-weight: 750; }.student-cell > div { display: grid; gap: 3px; }.student-cell strong { font-size: 14px; }.student-cell small { color: var(--ink-muted); font-size: 11px; }.table-status { display: inline-flex; align-items: center; gap: 7px; color: #8a5611; font-size: 12px; font-weight: 650; }.table-status > span { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }.table-status.is-executing, .table-status.is-adjusted, .table-status.is-archived { color: #23764a; }
@media (max-width: 1100px) { .summary-strip { flex-direction: column; }.summary-total { min-height: 100px; }.summary-facts { min-height: 100px; }.summary-facts > div { padding: 18px; } }
@media (max-width: 760px) { .page-head, .list-toolbar { align-items: stretch; flex-direction: column; }.summary-facts { grid-template-columns: repeat(2, 1fr); }.summary-facts > div:nth-child(3) { border-left: 0; }.summary-facts > div:nth-child(n+3) { border-top: 1px solid var(--line); }.filters { flex-wrap: wrap; }.filters :deep(.el-input) { width: 100%; }.filters :deep(.el-select) { flex: 1; } }
</style>
