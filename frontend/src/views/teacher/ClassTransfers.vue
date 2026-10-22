<template>
  <div class="page transfer-page">
    <div class="page-header">
      <div><h1 class="page-title">批量调班</h1><p class="intro">按确认的名单调整同年级班级，保留学号与历史记录。</p></div>
      <el-button @click="$router.push('/teacher/classes')">返回班级管理</el-button>
    </div>
    <el-tabs v-model="tab">
      <el-tab-pane label="调整名单" name="edit">
        <section class="panel" aria-label="选择学生">
          <h2>选择原班级与学生</h2>
          <div class="toolbar">
            <label class="field-label" for="transfer-source-class">原班级</label>
            <el-select id="transfer-source-class" v-model="sourceId" placeholder="选择原班级后展示学生名单" filterable aria-label="原班级" :disabled="submitting" @change="loadRoster">
              <el-option v-for="cls in classes" :key="cls.id" :value="cls.id" :label="classLabel(cls)" />
            </el-select>
          </div>
          <template v-if="sourceId">
            <div class="roster-heading">
              <div><strong>学生名单</strong><span class="help">共 {{ roster.length }} 人，已选 {{ selection.length }} 人，可单选或多选</span></div>
              <el-input v-model="studentKeyword" placeholder="搜索姓名或学号" clearable :disabled="submitting" aria-label="搜索班级学生" />
            </div>
            <div v-if="rosterError" class="roster-error" role="alert">{{ rosterError }}<el-button link type="primary" @click="loadRoster">重新加载</el-button></div>
            <el-table v-else ref="rosterTable" :data="filteredRoster" row-key="id" v-loading="rosterLoading" max-height="340" :empty-text="rosterLoading ? '正在加载学生名单…' : studentKeyword ? '未找到匹配的学生' : '该班暂无学生'" @selection-change="selection = $event">
              <el-table-column type="selection" reserve-selection width="48" :selectable="() => !submitting" />
              <el-table-column prop="name" label="姓名" min-width="100" />
              <el-table-column prop="username" label="学号" min-width="160" />
            </el-table>
            <div class="target-panel">
              <label class="field-label" for="transfer-target-class">将所选 {{ selection.length }} 名学生调至</label>
              <div class="toolbar target-toolbar">
                <el-select id="transfer-target-class" v-model="targetId" placeholder="勾选学生后选择目标班级" filterable aria-label="目标班级" :disabled="!selection.length || rosterLoading || submitting">
                  <el-option v-for="cls in targets" :key="cls.id" :value="cls.id" :label="classLabel(cls)" />
                </el-select>
                <el-button type="primary" :disabled="!selection.length || !targetId || submitting" @click="addSelected">加入调班名单（{{ selection.length }}）</el-button>
              </div>
              <p v-if="!rosterLoading && roster.length && !targets.length" class="help">暂无符合条件的目标班级，请先在班级管理中创建同学年、同年级、同班型的目标班级。</p>
              <p v-else class="help">加入名单后，在下方预览并确认生效。</p>
            </div>
          </template>
          <p v-else class="roster-placeholder">先选择原班级，这里会展示学生名单，支持勾选一个或多个学生。</p>
        </section>
        <section class="panel" aria-label="调班预览">
          <div class="section-title"><h2>待调整名单 <span>共 {{ rows.length }} 人</span></h2><el-button v-if="rows.length" link type="danger" :disabled="submitting" @click="rows = []; preview = null">清空名单</el-button></div>
          <el-table :data="rows" empty-text="请先选择原班级，勾选学生并指定目标班级" max-height="500">
            <el-table-column prop="student_username" label="学号" min-width="150" />
            <el-table-column label="姓名" width="100"><template #default="{ row, $index }">{{ preview?.rows[$index]?.student_name || row.student_name || '预览时核对' }}</template></el-table-column>
            <el-table-column label="原班级" min-width="140"><template #default="{ row, $index }">{{ preview?.rows[$index]?.source_class_name || classes.find(c => c.id === row.source_class_id)?.name || '自动匹配' }}</template></el-table-column>
            <el-table-column label="目标班级" min-width="180"><template #default="{ row }"><el-select v-model="row.target_class_id" filterable aria-label="目标班级"><el-option v-for="cls in classes" :key="cls.id" :value="cls.id" :label="classLabel(cls)" /></el-select></template></el-table-column>
            <el-table-column label="交接校验" min-width="230"><template #default="{ $index }">
              <template v-if="preview?.rows[$index]">
                <div v-for="error in preview.rows[$index].errors" :key="error" class="error-text">{{ error }}</div>
                <div v-if="!preview.rows[$index].errors.length">可交接 · {{ preview.rows[$index].case_count }} 份当前档案</div>
                <div v-for="assignment in preview.rows[$index].assignments.filter(a => a.options.length > 1)" :key="assignment.subject" class="assignment">
                  <label>{{ assignment.subject }}接手老师</label>
                  <el-select :model-value="rows[$index].subject_teachers[assignment.subject] || assignment.teacher_id" placeholder="请选择" :aria-label="`${assignment.subject}接手老师`" @update:model-value="rows[$index].subject_teachers[assignment.subject] = $event">
                    <el-option v-for="teacher in assignment.options" :key="teacher.id" :label="teacher.name" :value="teacher.id" />
                  </el-select>
                </div>
              </template><span v-else class="help">待预览</span>
            </template></el-table-column>
            <el-table-column label="操作" width="65"><template #default="{ $index }"><el-button link type="danger" :disabled="submitting" @click="removeRow($index)">移除</el-button></template></el-table-column>
          </el-table>
          <div v-if="preview" class="preview-summary" role="status">
            <strong>{{ fresh ? (preview.valid ? '校验通过' : '请修正名单后重新预览') : '名单已修改，请重新预览' }}</strong>
            <span v-for="cls in preview.classes" :key="cls.class_id">{{ cls.class_name }}：{{ cls.before }} → {{ cls.after }} 人</span>
          </div>
          <p class="help">学号、家长关联和历史成绩保留；当前档案及未完成事项交接给新老师。过去月份和已发布月评只读保留，当月未发布月评继续填写。</p>
          <el-form label-position="top"><el-form-item label="调班原因" required><el-input v-model="reason" maxlength="500" show-word-limit placeholder="例如：高三年级教学安排调整" /></el-form-item></el-form>
          <div class="footer-actions">
            <el-button :loading="previewing" :disabled="!rows.length || submitting" @click="runPreview">预览调整</el-button>
            <el-button type="primary" :loading="submitting" :disabled="!fresh || !preview?.valid || !reason.trim() || previewing" @click="submit">确认并立即生效</el-button>
          </div>
          <p v-if="result" class="success-text" role="status">批次 #{{ result.id }} 已生效，共调整 {{ result.student_count }} 名学生。可在调班记录中查看。</p>
        </section>
      </el-tab-pane>
      <el-tab-pane label="调班记录" name="history">
        <section class="panel" v-loading="historyLoading">
          <el-empty v-if="!history.items.length" description="暂无调班记录" />
          <article v-for="batch in history.items" :key="batch.id" class="history-batch">
            <h2>批次 #{{ batch.id }} · {{ batch.student_count }} 人</h2>
            <p class="help">{{ formatTime(batch.created_at) }} · {{ batch.actor_name }} · {{ batch.reason }}</p>
            <el-table :data="batch.items"><el-table-column prop="student_username" label="学号" min-width="150" /><el-table-column prop="student_name" label="姓名" min-width="100" /><el-table-column prop="source_class_name" label="原班级" min-width="140" /><el-table-column prop="target_class_name" label="目标班级" min-width="140" /></el-table>
          </article>
          <el-pagination v-if="history.total" layout="prev, pager, next" :total="history.total" :page-size="10" v-model:current-page="historyPage" @current-change="loadHistory" />
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listClasses, listStudents, previewTransfers, commitTransfers, listTransfers } from '../../api/classes'

const classes = ref([]), sourceId = ref(null), targetId = ref(null), roster = ref([]), selection = ref([])
const rosterTable = ref(null), studentKeyword = ref(''), rosterError = ref('')
const rows = ref([]), reason = ref(''), preview = ref(null), fresh = ref(false)
const previewing = ref(false), submitting = ref(false), rosterLoading = ref(false), result = ref(null)
const tab = ref('edit'), history = ref({ items: [], total: 0 }), historyPage = ref(1), historyLoading = ref(false)
let requestId = '', rosterRequest = 0
const classLabel = c => `${c.name} · ${c.school_year} · ID ${c.id}`
const formatTime = value => new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
const targets = computed(() => {
  const source = classes.value.find(c => c.id === sourceId.value)
  return classes.value.filter(c => source && c.id !== source.id && ['school_year', 'education_stage', 'grade', 'class_type', 'short_term_type'].every(k => c[k] === source[k]))
})
const filteredRoster = computed(() => {
  const keyword = studentKeyword.value.trim().toLocaleLowerCase()
  return roster.value.filter(s => `${s.name} ${s.username}`.toLocaleLowerCase().includes(keyword))
})
watch(rows, () => { fresh.value = false }, { deep: true, flush: 'sync' })
watch(tab, value => { if (value === 'history') loadHistory() })
async function loadRoster() {
  const version = ++rosterRequest
  rosterTable.value?.clearSelection()
  selection.value = []; targetId.value = null; roster.value = []; studentKeyword.value = ''; rosterError.value = ''; rosterLoading.value = true
  try { const data = await listStudents(sourceId.value); if (version === rosterRequest) roster.value = data }
  catch { if (version === rosterRequest) { roster.value = []; rosterError.value = '学生名单加载失败，请重试。' } }
  finally { if (version === rosterRequest) rosterLoading.value = false }
}
function addSelected() {
  const additions = selection.value.map(s => ({ student_username: s.username, student_name: s.name,
    source_class_id: sourceId.value, target_class_id: targetId.value, subject_teachers: {} }))
  addRows(additions)
}
function addRows(additions) {
  if (rows.value.length + additions.length > 500) return ElMessage.warning('每批最多调整 500 人')
  const seen = new Set(rows.value.map(r => r.student_username))
  for (const row of additions) { if (seen.has(row.student_username)) return ElMessage.warning(`学号 ${row.student_username} 重复，请核对`); seen.add(row.student_username) }
  rows.value.push(...additions); preview.value = null; result.value = null
}
function removeRow(index) { rows.value.splice(index, 1); preview.value = null }
async function runPreview() {
  previewing.value = true; fresh.value = false
  const snapshot = JSON.stringify(rows.value)
  try {
    const data = await previewTransfers({ rows: JSON.parse(snapshot) })
    if (JSON.stringify(rows.value) !== snapshot) return
    preview.value = data; fresh.value = true; requestId = crypto.randomUUID()
  } catch { fresh.value = false } finally { previewing.value = false }
}
async function submit() {
  try { await ElMessageBox.confirm(`确认立即调整 ${rows.value.length} 名学生？当前档案与未完成事项将一并交接。`, '确认批量调班', { confirmButtonText: '确认生效', cancelButtonText: '返回核对' }) }
  catch { return }
  if (!fresh.value || !preview.value?.valid) return
  submitting.value = true
  try {
    result.value = await commitTransfers({ rows: rows.value, reason: reason.value.trim(), preview_token: preview.value.preview_token, request_id: requestId })
    rows.value = []; preview.value = null; reason.value = ''
    if (sourceId.value) await loadRoster()
    ElMessage.success('调班已生效')
  } catch (error) { if (error.response?.status === 409) fresh.value = false } finally { submitting.value = false }
}
async function loadHistory() {
  historyLoading.value = true
  try { history.value = await listTransfers({ offset: (historyPage.value - 1) * 10, limit: 10 }) }
  finally { historyLoading.value = false }
}
onMounted(async () => { classes.value = await listClasses() })
</script>

<style scoped>
.transfer-page { max-width: 1400px; margin: auto; }
.intro, .help { color: #445269; font-size: 14px; line-height: 1.6; }
.intro { margin: 6px 0 0; }
.panel { background: #fff; border: 1px solid #e5eaf2; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
h2 { margin: 0 0 16px; font-size: 16px; font-weight: 600; color: #172033; }
h2 span { font-size: 14px; font-weight: 400; color: #445269; margin-left: 12px; }
.toolbar { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.toolbar { align-items: center; }
.toolbar .el-select { width: 270px; max-width: 100%; }
.field-label { font-size: 14px; font-weight: 600; color: #172033; }
.roster-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin: 20px 0 12px; }
.roster-heading strong { font-size: 14px; margin-right: 12px; }
.roster-heading .el-input { width: 240px; max-width: 100%; }
.roster-placeholder { padding: 24px 0; color: #445269; font-size: 14px; }
.roster-error { color: #b42318; padding: 16px 0; display: flex; align-items: center; gap: 12px; }
.target-panel { margin-top: 20px; padding-top: 16px; border-top: 1px solid #e5eaf2; }
.target-toolbar { margin: 10px 0 0; }
.target-panel p { margin-bottom: 0; }
.footer-actions, .section-title { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.section-title { justify-content: space-between; }
.error-text { color: #b42318; line-height: 1.6; }
.assignment { display: grid; gap: 4px; margin-top: 8px; }
.preview-summary { display: flex; flex-wrap: wrap; gap: 8px 20px; padding: 16px 0; color: #172033; }
.success-text { color: #166534; }
.history-batch + .history-batch { margin-top: 28px; padding-top: 20px; border-top: 1px solid #e5eaf2; }
@media (max-width: 720px) { .panel { padding: 14px; } .page-header { align-items: flex-start; flex-wrap: wrap; gap: 12px; } .toolbar .el-select { width: 100%; } .footer-actions { justify-content: flex-end; } }
</style>
