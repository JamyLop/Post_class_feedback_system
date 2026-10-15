<template>
  <section class="writing-status" aria-label="月度评定填写状态查询">
    <div class="query-controls">
      <el-select v-model="classId" aria-label="班级" placeholder="全部班级" clearable @change="query">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-date-picker v-model="month" aria-label="评定月份" type="month" value-format="YYYY-MM" :clearable="false" @change="query" />
      <el-select v-model="status" aria-label="填写状态" @change="query">
        <el-option label="全部填写状态" value="" />
        <el-option label="已填写" value="written" />
        <el-option label="未填写" value="unwritten" />
      </el-select>
      <el-input v-model="keyword" aria-label="搜索学生" placeholder="搜索学生，回车查询" clearable @keyup.enter="query" @clear="query" />
      <el-button :loading="loading" @click="query">查询</el-button>
    </div>
    <p class="query-note">按本人负责的评定项统计，兼任班主任和学科老师时分别显示德育与学科。</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-else>
      <p class="counts" aria-live="polite">共 {{ result.total }} 项 · 已填写 {{ result.written }} 项 · 未填写 {{ result.unwritten }} 项</p>
      <el-table v-loading="loading" :data="result.items" empty-text="当前条件下没有学生，请调整班级、月份或填写状态">
        <el-table-column prop="student_name" label="学生" min-width="100" />
        <el-table-column prop="class_name" label="班级" min-width="120" />
        <el-table-column prop="month_label" label="月份" width="110" />
        <el-table-column prop="subject" label="本人负责内容" min-width="130" />
        <el-table-column label="填写状态" width="110"><template #default="{ row }"><el-tag :type="row.writing_status === 'written' ? 'success' : 'warning'">{{ row.writing_status === 'written' ? '已填写' : '未填写' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="130"><template #default="{ row }"><el-button link type="primary" :disabled="loading || opening" @click="openEditor(row)">{{ row.writing_status === 'written' ? '查看 / 修改' : '去填写' }}</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-if="result.filtered_total > 50" v-model:current-page="page" :page-size="50" :total="result.filtered_total" layout="prev, pager, next, total" @current-change="load" />
    </template>
    <el-dialog v-model="editing" title="填写月度评定" width="min(560px, 92vw)" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving" append-to-body>
      <template v-if="current">
        <p>{{ current.student_name }} · {{ current.class_name }} · {{ current.month_label }} · {{ current.subject }}</p>
        <el-form label-position="top"><MonthlyReviewForm v-model="content" :limit="current.teacher_role === 'subject_teacher' ? 600 : 2400" :disabled="saving" /></el-form>
      </template>
      <template #footer><el-button :disabled="saving" @click="editing = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!completeReview(content)" @click="save">保存评定</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
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
const result = ref({ total: 0, written: 0, unwritten: 0, filtered_total: 0, items: [] })
const error = ref('')
const loading = ref(false)
const opening = ref(false)
const editing = ref(false)
const saving = ref(false)
const current = ref(null)
const content = ref('')
let requestId = 0

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await listMonthlyWritingStatus({ month_label: month.value, class_id: classId.value || undefined, writing_status: status.value || undefined, keyword: keyword.value.trim(), offset: (page.value - 1) * 50, limit: 50 })
    if (id === requestId) result.value = data
  } catch {
    if (id === requestId) error.value = '填写状态加载失败，请点击查询重试'
  } finally { if (id === requestId) loading.value = false }
}
function query() { page.value = 1; load() }
async function openEditor(row) {
  opening.value = true
  try {
    const report = row.report_id ? await getMonthlyReport(row.report_id) : null
    current.value = row
    content.value = row.teacher_role === 'head_teacher' ? report?.final_content || '' : report?.evaluations?.find(e => e.teacher_role === 'subject_teacher' && e.teacher_id === auth.user?.id)?.content || ''
    editing.value = true
  } finally { opening.value = false }
}
const auth = useAuthStore()
async function save() {
  if (saving.value || !completeReview(content.value)) return
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
    query()
  } finally { saving.value = false }
}
onMounted(load)
</script>

<style scoped>
.writing-status { background: var(--surface, #fff); border: 1px solid var(--line, #e5eaf2); border-radius: 8px; padding: 18px; }
.query-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.query-controls > .el-select, .query-controls > .el-input { width: 180px; }
.query-controls > .el-date-editor { width: 160px; flex: none; }
.query-note { color: var(--ink-secondary, #445269); font-size: 13px; line-height: 1.6; margin: 14px 0; }
.counts { font-size: 14px; color: var(--ink, #172033); font-variant-numeric: tabular-nums; }
.el-pagination { margin-top: 16px; flex-wrap: wrap; }
@media (max-width: 600px) { .query-controls > .el-select, .query-controls > .el-input, .query-controls > .el-date-editor { width: 100%; } }
</style>
