<template>
  <section class="page monthly-page">
    <header class="page-head">
      <div>
        <div class="scope-line"><span>高三试点</span><span>月报 · AI总结</span></div>
        <h1>月报管理</h1>
        <p>按自然月 AI 汇总学情与德育表现，生成“学情总结 / 德育表现 / 改进方案”三段式月报，班主任可编辑后发布给家长/学生。</p>
      </div>
      <el-button type="primary" @click="openGenerate"><el-icon><Plus /></el-icon>生成月报</el-button>
    </header>

    <section class="filter-surface">
      <div class="filters">
        <el-select v-model="filters.class_id" placeholder="选择班级" clearable style="width: 180px" @change="load">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filters.student_id" placeholder="选择学生" clearable style="width: 180px" @change="load">
          <el-option v-for="s in allStudents" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-date-picker v-model="filters.month_label" type="month" placeholder="月份" value-format="YYYY-MM" style="width: 160px" @change="load" />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="load">
          <el-option label="生成中" value="generating" /><el-option label="待发布" value="generated" /><el-option label="已发布" value="published" /><el-option label="失败" value="failed" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      </div>
    </section>

    <section class="list-surface">
      <el-table v-loading="loading" :data="rows" empty-text="暂无月报">
        <el-table-column prop="month_label" label="月份" width="110" />
        <el-table-column label="学生" min-width="130"><template #default="{ row }">{{ row.student_name || `学生#${row.student_id}` }}</template></el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column prop="period_start" label="周期" min-width="180"><template #default="{ row }">{{ row.period_start }} ~ {{ row.period_end }}</template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看/编辑</el-button>
            <el-button v-if="row.status==='generated'" link type="success" @click="publishRow(row)">发布</el-button>
            <el-button v-if="['generating','failed'].includes(row.status)" link @click="regenerate(row)">重新生成</el-button>
            <el-button link type="danger" @click="removeRow(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 生成 -->
    <el-dialog v-model="genVisible" title="生成月报（AI总结）" width="560px" destroy-on-close>
      <div class="gen-tip">将汇总当月的周测成绩、作业得分、知识点薄弱点、德育行为记录与任务执行，AI 生成三段式初稿。</div>
      <el-form label-position="top">
        <el-form-item label="班级"><el-select v-model="genForm.class_id" style="width: 100%" @change="onGenClassChange"><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="学生"><el-select v-model="genForm.student_id" filterable style="width: 100%"><el-option v-for="s in genStudents" :key="s.id" :label="`${s.name}（${s.username}）`" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="月份"><el-date-picker v-model="genForm.month_label" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width: 100%" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="genVisible=false">取消</el-button><el-button type="primary" :loading="generating" @click="submitGenerate">生成</el-button></template>
    </el-dialog>

    <!-- 详情/编辑 -->
    <el-dialog v-model="detailVisible" title="月报详情" width="760px" destroy-on-close>
      <template v-if="current">
        <div class="detail-meta">
          <span>{{ current.student_name }} · {{ current.class_name }} · {{ current.month_label }}</span>
          <el-tag :type="statusType(current.status)">{{ statusText(current.status) }}</el-tag>
        </div>
        <el-alert v-if="current.error_message" type="error" :title="current.error_message" :closable="false" style="margin: 12px 0" />
        <div class="report-sections" v-if="current.status!=='generating'">
          <div class="ai-label">AI 初稿（只读）</div>
          <el-input :model-value="current.ai_content" type="textarea" :autosize="{minRows:4,maxRows:12}" readonly />
          <div class="ai-label" style="margin-top: 14px">班主任定稿（可修改）</div>
          <el-input v-model="editContent" type="textarea" :autosize="{minRows:8,maxRows:20}" placeholder="可直接修改 AI 初稿，补充德育观察与下月改进细节" :disabled="!['generated','published'].includes(current.status)" maxlength="8000" show-word-limit />
          <div class="meta-line">模型：{{ current.model_name || '-' }} · 耗时：{{ current.duration_ms }}ms · Token：{{ current.total_tokens }}</div>
        </div>
        <el-empty v-else description="AI 正在生成中，请稍后刷新" />
      </template>
      <template #footer>
        <el-button @click="detailVisible=false">关闭</el-button>
        <el-button :loading="saving" :disabled="!current || !['generated','published'].includes(current.status)" @click="saveEdit">保存修改</el-button>
        <el-button v-if="current && current.status==='generated'" type="primary" :loading="saving" @click="publishCurrent">发布</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { listClasses, listStudents } from '../../api/classes'
import { listUsers } from '../../api/classes'
import { deleteMonthlyReport, generateMonthlyReport, listMonthlyReports, publishMonthlyReport, updateMonthlyReport } from '../../api/monthlyReports'

const classes = ref([])
const allStudents = ref([])
const rows = ref([])
const loading = ref(false)
const generating = ref(false)
const saving = ref(false)

const filters = ref({ class_id: null, student_id: null, month_label: '', status: '' })
const genVisible = ref(false)
const genForm = ref({ class_id: null, student_id: null, month_label: new Date().toISOString().slice(0,7) })
const genStudents = ref([])
const detailVisible = ref(false)
const current = ref(null)
const editContent = ref('')

const statusText = (s) => ({ generating:'生成中', generated:'待发布', published:'已发布', failed:'生成失败'}[s] || s)
const statusType = (s) => ({ generated:'warning', published:'success', failed:'danger'}[s] || 'info')

async function load() {
  loading.value = true
  try { rows.value = await listMonthlyReports({ ...filters.value }) } finally { loading.value = false }
}
async function onGenClassChange(cid) {
  genForm.value.student_id = null
  genStudents.value = cid ? await listStudents(cid) : []
}
function openGenerate() {
  genForm.value = { class_id: filters.value.class_id || classes.value[0]?.id || null, student_id: null, month_label: new Date().toISOString().slice(0,7) }
  if (genForm.value.class_id) onGenClassChange(genForm.value.class_id)
  genVisible.value = true
}
async function submitGenerate() {
  if (!genForm.value.class_id || !genForm.value.student_id || !genForm.value.month_label) { ElMessage.warning('请选择班级、学生和月份'); return }
  generating.value = true
  try {
    await generateMonthlyReport(genForm.value)
    ElMessage.success('月报生成任务已启动，稍后刷新查看')
    genVisible.value = false
    await load()
  } finally { generating.value = false }
}
async function openDetail(row) {
  current.value = row
  editContent.value = row.final_content || row.ai_content || ''
  detailVisible.value = true
}
async function saveEdit() {
  if (!editContent.value.trim()) { ElMessage.warning('内容不能为空'); return }
  saving.value = true
  try {
    const updated = await updateMonthlyReport(current.value.id, { final_content: editContent.value })
    current.value = updated
    ElMessage.success('已保存')
    await load()
  } finally { saving.value = false }
}
async function publishRow(row) { await publishMonthlyReport(row.id); ElMessage.success('已发布'); await load() }
async function publishCurrent() { await publishRow(current.value); current.value.status='published'; await load() }
async function regenerate(row) {
  await generateMonthlyReport({ student_id: row.student_id, class_id: row.class_id, month_label: row.month_label })
  ElMessage.success('已重新生成')
  await load()
}
async function removeRow(row) {
  await ElMessageBox.confirm(`确认删除 ${row.month_label} 月报？`, '删除确认', { type:'warning' })
  await deleteMonthlyReport(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(async () => {
  classes.value = await listClasses()
  try { allStudents.value = await listUsers('student') } catch { allStudents.value = [] }
  await load()
})
</script>

<style scoped>
.monthly-page { display: grid; gap: 18px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
.scope-line { display: flex; gap: 8px; margin-bottom: 10px; }
.scope-line span { padding: 5px 10px; color: var(--brand-strong); background: var(--brand-soft); border: 1px solid color-mix(in oklch, var(--brand) 10%, transparent); border-radius: 999px; font-size: 11.5px; font-weight: 700; }
.scope-line span + span { color: var(--ink-secondary); background: var(--surface); border-color: var(--line); }
.page-head h1 { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.03em; }
.page-head p { margin: 6px 0 0; color: var(--ink-secondary); font-size: 13px; max-width: 68ch; line-height: 1.6; }
.filter-surface, .list-surface { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-soft); padding: 16px 18px; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.gen-tip { color: var(--ink-muted); font-size: 12px; margin-bottom: 10px; line-height: 1.6; }
.detail-meta { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-weight: 600; }
.ai-label { font-size: 12px; font-weight: 700; color: var(--ink); margin-bottom: 6px; }
.meta-line { color: #909399; font-size: 12px; margin-top: 8px; }
@media (max-width: 760px) { .page-head { flex-direction: column; } }
</style>
