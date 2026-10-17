<template>
  <section class="writing-status" aria-label="月度评定填写状态查询">
    <div class="step-heading">
      <el-button v-if="selectedStudent" @click="backToStudents">返回学生列表</el-button>
      <h2>{{ selectedStudent ? `${selectedStudent.student_name} · 科目填写状态` : '学生填写进度' }}</h2>
      <span>{{ selectedStudent ? '第二步：选择科目' : '第一步：选择学生' }}</span>
    </div>
    <div v-if="!selectedStudent" class="query-controls">
      <el-select v-model="classId" aria-label="班级" placeholder="全部班级" clearable @change="query">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-date-picker v-model="month" aria-label="评定月份" type="month" value-format="YYYY-MM" :clearable="false" @change="query" />
      <el-select v-model="status" aria-label="填写状态" placeholder="全部学生" @change="query">
        <el-option label="全部学生" value="" />
        <el-option label="有已填写项" value="written" />
        <el-option label="有未填写项" value="unwritten" />
      </el-select>
      <el-input v-model="keyword" aria-label="搜索学生" placeholder="搜索学生，回车查询" clearable @keyup.enter="query" @clear="query" />
      <el-button :loading="loading" @click="query">查询</el-button>
    </div>
    <p class="query-note">{{ selectedStudent ? `${selectedStudent.class_name} · ${selectedStudent.month_label}，点击科目操作进入评定。` : '班主任查看所带学生全部老师的进度；任课老师查看本人负责内容。德育仅由班主任填写。' }}</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-button v-if="error" @click="load">重新加载</el-button>
    <template v-else>
      <p class="counts" aria-live="polite">{{ selectedStudent ? '' : `共 ${result.student_total} 名学生 · ` }}共 {{ result.total }} 项 · 已填写 {{ result.written }} 项 · 未填写 {{ result.unwritten }} 项</p>
      <el-table v-if="!selectedStudent" v-loading="loading" :data="result.students" empty-text="当前条件下没有学生，请调整筛选条件">
        <el-table-column label="学生" min-width="100"><template #default="{ row }"><el-button link type="primary" :disabled="loading" @click="selectStudent(row)">{{ row.student_name }}</el-button></template></el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="120" />
        <el-table-column label="未填写项数" min-width="130"><template #default="{ row }"><el-tag :type="row.unwritten ? 'warning' : 'success'">{{ row.unwritten ? `${row.unwritten} 项未填写` : '全部已填写' }}</el-tag></template></el-table-column>
        <el-table-column label="已填 / 应填" width="120"><template #default="{ row }">{{ row.written }} / {{ row.total }}</template></el-table-column>
        <el-table-column label="操作" width="130"><template #default="{ row }"><el-button link type="primary" :disabled="loading" @click="selectStudent(row)">查看科目</el-button></template></el-table-column>
      </el-table>
      <el-table v-else v-loading="loading" :data="result.items" empty-text="该学生暂无可查看的评定项">
        <el-table-column prop="subject" label="科目" min-width="130" />
        <el-table-column label="负责老师" min-width="130"><template #default="{ row }">{{ row.teacher_name }}{{ row.assignment_required ? '（待关联账号）' : '' }}</template></el-table-column>
        <el-table-column label="填写状态" width="110"><template #default="{ row }"><el-tag :type="row.writing_status === 'written' ? 'success' : 'warning'">{{ row.writing_status === 'written' ? '已填写' : '未填写' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="130"><template #default="{ row }"><el-button link type="primary" :disabled="loading || opening || (row.can_edit === false && row.writing_status !== 'written')" @click="openEditor(row)">{{ row.assignment_required ? '待确认任课老师' : row.can_edit === false ? (row.writing_status === 'written' ? '查看评定' : '待老师填写') : (row.writing_status === 'written' ? '查看 / 修改' : '去填写') }}</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-if="pageTotal > 50" v-model:current-page="page" :page-size="50" :total="pageTotal" layout="prev, pager, next, total" @current-change="load" />
    </template>
    <el-dialog v-model="editing" :title="readOnly ? '查看月度评定' : '填写月度评定'" width="min(560px, 92vw)" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving" append-to-body>
      <template v-if="current">
        <p>{{ current.student_name }} · {{ current.class_name }} · {{ current.month_label }} · {{ current.subject }}</p>
        <el-form label-position="top"><MonthlyReviewForm v-model="content" :limit="current.teacher_role === 'subject_teacher' ? 600 : 2400" :disabled="saving || readOnly" /></el-form>
      </template>
      <template #footer><el-button :disabled="saving" @click="editing = false">取消</el-button><el-button v-if="!readOnly" type="primary" :loading="saving" :disabled="!completeReview(content)" @click="save">保存评定</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import MonthlyReviewForm from './MonthlyReviewForm.vue'
import { completeReview } from '../utils/monthlyReview'
import { useAuthStore } from '../stores/auth'
import { createMonthlyReport, getMonthlyReport, listMonthlyReports, listMonthlyWritingStatus, saveMonthlyEvaluation, updateMonthlyReport } from '../api/monthlyReports'

defineProps({ classes: { type: Array, default: () => [] } })
const emit = defineEmits(['saved'])
const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const classId = ref(null)
const status = ref('')
const keyword = ref('')
const page = ref(1)
const result = ref({ total: 0, written: 0, unwritten: 0, filtered_total: 0, items: [], students: [], student_total: 0 })
const selectedStudent = ref(null)
const studentPage = ref(1)
const pageTotal = computed(() => selectedStudent.value ? result.value.filtered_total : result.value.student_total)
const error = ref('')
const loading = ref(false)
const opening = ref(false)
const editing = ref(false)
const saving = ref(false)
const current = ref(null)
const readOnly = computed(() => current.value?.can_edit === false)
const content = ref('')
let requestId = 0

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await listMonthlyWritingStatus({ month_label: month.value, class_id: selectedStudent.value?.class_id || classId.value || undefined, view: selectedStudent.value ? 'items' : 'students', student_id: selectedStudent.value?.student_id, writing_status: selectedStudent.value ? undefined : status.value || undefined, keyword: selectedStudent.value ? undefined : keyword.value.trim(), offset: (page.value - 1) * 50, limit: 50 })
    if (id === requestId) {
      result.value = data
      const lastPage = Math.max(1, Math.ceil(pageTotal.value / 50))
      if (page.value > lastPage) { page.value = lastPage; return load() }
    }
  } catch {
    if (id === requestId) error.value = '填写状态加载失败，请点击查询重试'
  } finally { if (id === requestId) loading.value = false }
}
function query() { page.value = 1; load() }
function selectStudent(row) { studentPage.value = page.value; selectedStudent.value = row; page.value = 1; load() }
function backToStudents() { selectedStudent.value = null; page.value = studentPage.value; load() }
async function openEditor(row) {
  opening.value = true
  try {
    const report = row.report_id ? await getMonthlyReport(row.report_id) : null
    current.value = row
    content.value = row.teacher_role === 'head_teacher' ? report?.final_content || '' : report?.evaluations?.find(e => e.teacher_role === 'subject_teacher' && e.teacher_id === (row.teacher_id ?? auth.user?.id))?.content || ''
    editing.value = true
  } catch { ElMessage.error('评定加载失败，请重试') } finally { opening.value = false }
}
const auth = useAuthStore()
async function save() {
  if (saving.value || readOnly.value || !completeReview(content.value)) return
  saving.value = true
  try {
    const row = current.value
    // 补填前重新查询，其他老师可能已在打开表单期间创建同月评定。
    const existing = (await listMonthlyReports({ class_id: row.class_id, student_id: row.student_id, month_label: row.month_label }))[0]
    if (existing) {
      if (row.teacher_role === 'head_teacher') await updateMonthlyReport(existing.id, { final_content: content.value })
      else await saveMonthlyEvaluation(existing.id, { content: content.value })
    } else {
      await createMonthlyReport({ class_id: row.class_id, student_id: row.student_id, month_label: row.month_label, final_content: content.value, evaluation_role: row.teacher_role })
    }
    editing.value = false
    ElMessage.success('月度评定已保存')
    emit('saved')
    load()
  } catch { ElMessage.error('保存失败，请重试，填写内容已保留') } finally { saving.value = false }
}
onMounted(load)
</script>

<style scoped>
.writing-status { background: var(--surface, #fff); border: 1px solid var(--line, #e5eaf2); border-radius: 8px; padding: 18px; }
.step-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; }
.step-heading h2 { margin: 0; font-size: 18px; color: var(--ink, #172033); }
.step-heading span { color: var(--ink-secondary, #445269); font-size: 13px; }
.query-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.query-controls > .el-select, .query-controls > .el-input { width: 180px; }
.query-controls > .el-date-editor { width: 160px; flex: none; }
.query-note { color: var(--ink-secondary, #445269); font-size: 13px; line-height: 1.6; margin: 14px 0; }
.counts { font-size: 14px; color: var(--ink, #172033); font-variant-numeric: tabular-nums; }
:deep(.el-tag--warning) { color: #865c1e; background-color: #fbf1df; }
:deep(.el-tag--success) { color: #286349; background-color: #eaf3ee; }
.el-pagination { margin-top: 16px; flex-wrap: wrap; }
@media (max-width: 600px) { .query-controls > .el-select, .query-controls > .el-input, .query-controls > .el-date-editor { width: 100%; } }
</style>
