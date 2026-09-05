<template>
  <section class="page monthly-page">
    <header class="page-head">
      <div>
        <div class="scope-line"><span>高三试点</span><span>月度评定 · 教师填写</span></div>
        <h1>月度评定管理</h1>
        <p>按自然月手动填写学情、德育表现与改进建议，保存后审阅并发布给家长和学生。</p>
      </div>
      <el-button type="primary" @click="openGenerate"><el-icon><Plus /></el-icon>新建月度评定</el-button>
    </header>

    <section class="filter-surface">
      <div class="filters">
        <el-select v-model="filters.class_id" placeholder="选择班级" clearable style="width: 180px" @change="onFilterClassChange">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filters.student_id" placeholder="选择学生" clearable style="width: 180px" @change="load" :disabled="filters.class_id && !filterStudents.length">
          <el-option v-for="s in filterStudents" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-date-picker v-model="filters.month_label" type="month" placeholder="月份" value-format="YYYY-MM" style="width: 160px" @change="load" />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="load">
          <el-option label="待填写" value="generating" /><el-option label="待发布" value="generated" /><el-option label="已发布" value="published" /><el-option label="待补充" value="failed" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      </div>
    </section>

    <section class="list-surface">
      <el-table v-loading="loading" :data="rows" empty-text="暂无月度评定">
        <el-table-column prop="month_label" label="月份" width="110" />
        <el-table-column label="学生" min-width="130"><template #default="{ row }">{{ row.student_name || `学生#${row.student_id}` }}</template></el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column prop="period_start" label="周期" min-width="180"><template #default="{ row }">{{ row.period_start }} ~ {{ row.period_end }}</template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看/编辑</el-button>
            <el-button v-if="row.status==='generated'" link type="success" @click="publishRow(row)">发布</el-button>
            <el-button link type="danger" @click="removeRow(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 手动填写 -->
    <el-dialog v-model="genVisible" title="填写月度评定" width="560px" destroy-on-close>
      <div class="gen-tip">选择学生与月份，填写评定内容后保存为待发布。</div>
      <el-form label-position="top">
        <el-form-item label="班级"><el-select v-model="genForm.class_id" style="width: 100%" @change="onGenClassChange"><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="学生"><el-select v-model="genForm.student_id" filterable style="width: 100%"><el-option v-for="s in genStudents" :key="s.id" :label="`${s.name}（${s.username}）`" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="月份"><el-date-picker v-model="genForm.month_label" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width: 100%" /></el-form-item>
        <el-form-item label="评定内容" required><el-input v-model="genForm.final_content" type="textarea" :rows="8" maxlength="8000" show-word-limit placeholder="请填写本月学情、德育表现及下月改进建议" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="genVisible=false">取消</el-button><el-button type="primary" :loading="generating" @click="submitGenerate">保存待发布</el-button></template>
    </el-dialog>

    <!-- 详情/编辑 -->
    <el-dialog v-model="detailVisible" title="月度评定详情" width="760px" destroy-on-close>
      <template v-if="current">
        <div class="detail-meta">
          <span>{{ current.student_name }} · {{ current.class_name }} · {{ current.month_label }}</span>
          <el-tag :type="statusType(current.status)">{{ statusText(current.status) }}</el-tag>
        </div>
        <el-alert v-if="current.error_message" type="error" :title="current.error_message" :closable="false" style="margin: 12px 0" />
        <div class="report-sections" >
          <div class="ai-label" style="margin-top: 14px">班主任定稿（可修改）</div>
          <el-input v-model="editContent" type="textarea" :autosize="{minRows:8,maxRows:20}" placeholder="请填写本月学情、德育表现及下月改进建议"  maxlength="8000" show-word-limit />
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible=false">关闭</el-button>
        <el-button :loading="saving" :disabled="!current" @click="saveEdit">保存修改</el-button>
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
import { deleteMonthlyReport, createMonthlyReport, listMonthlyReports, publishMonthlyReport, updateMonthlyReport } from '../../api/monthlyReports'

const classes = ref([])
const allStudents = ref([])
const filterStudents = ref([])
const rows = ref([])
const loading = ref(false)
const generating = ref(false)
const saving = ref(false)

const filters = ref({ class_id: null, student_id: null, month_label: '', status: '' })
const genVisible = ref(false)
const genForm = ref({ class_id: null, student_id: null, month_label: new Date().toISOString().slice(0,7), final_content: '' })
const genStudents = ref([])
const detailVisible = ref(false)
const current = ref(null)
const editContent = ref('')

const statusText = (s) => ({ generating:'待填写', generated:'待发布', published:'已发布', failed:'待补充'}[s] || s)
const statusType = (s) => ({ generated:'warning', published:'success', failed:'danger'}[s] || 'info')

async function load() {
  loading.value = true
  try { rows.value = await listMonthlyReports({ ...filters.value }) } finally { loading.value = false }
}
async function onFilterClassChange(cid) {
  // 切换班级时清空已选学生，避免跨班数据泄漏；学生下拉按班级重新拉取
  filters.value.student_id = null
  if (cid) {
    try { filterStudents.value = await listStudents(cid) } catch { filterStudents.value = [] }
  } else {
    filterStudents.value = [...allStudents.value]
  }
  await load()
}
async function onGenClassChange(cid) {
  genForm.value.student_id = null
  genStudents.value = cid ? await listStudents(cid) : []
}
function openGenerate() {
  genForm.value = { class_id: filters.value.class_id || classes.value[0]?.id || null, student_id: null, month_label: new Date().toISOString().slice(0,7), final_content: '' }
  if (genForm.value.class_id) onGenClassChange(genForm.value.class_id)
  genVisible.value = true
}
async function submitGenerate() {
  if (!genForm.value.class_id || !genForm.value.student_id || !genForm.value.month_label) { ElMessage.warning('请选择班级、学生和月份'); return }
  if (generating.value) return
  if (!genForm.value.final_content.trim()) { ElMessage.warning('请填写评定内容'); return }
  generating.value = true
  try {
    await createMonthlyReport(genForm.value)
    ElMessage.success('月度评定已保存待发布')
    genVisible.value = false
    await load()
  } finally { generating.value = false }
}
async function openDetail(row) {
  current.value = row
  editContent.value = row.final_content || ''
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
async function publishCurrent() {
  if (saving.value) return
  if (!editContent.value.trim()) { ElMessage.warning('内容不能为空'); return }
  saving.value = true
  try {
    // 发布前保存当前编辑框，避免发布仍停留在数据库里的旧正文。
    current.value = await updateMonthlyReport(current.value.id, { final_content: editContent.value.trim() })
    current.value = await publishMonthlyReport(current.value.id)
    ElMessage.success('已发布')
    await load()
  } finally { saving.value = false }
}
async function removeRow(row) {
  await ElMessageBox.confirm(`确认删除 ${row.month_label} 月度评定？`, '删除确认', { type:'warning' })
  await deleteMonthlyReport(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(async () => {
  classes.value = await listClasses()
  try { allStudents.value = await listUsers('student') } catch { allStudents.value = [] }
  filterStudents.value = [...allStudents.value]
  // 若默认选中班级（例如只有一个班），可按需自动过滤；此处保持全量，需用户主动选班
  await load()
})
</script>

<style scoped>
.monthly-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.scope-line {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.scope-line span {
  font-size: 11px;
  font-weight: 600;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 6px;
}

.scope-line span + span {
  color: #64748b;
  background: #ffffff;
  border-color: #e2e8f0;
}

.page-head h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.page-head p {
  margin: 0;
  color: #64748b;
  font-size: 13.5px;
  max-width: 68ch;
  line-height: 1.5;
}

.filter-surface, .list-surface {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  padding: 16px 18px;
}

.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.gen-tip {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 16px;
  line-height: 1.5;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.detail-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 14px;
}

.ai-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 6px;
}

.meta-line {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 10px;
}

@media (max-width: 760px) {
  .page-head {
    flex-direction: column;
  }
}
</style>
