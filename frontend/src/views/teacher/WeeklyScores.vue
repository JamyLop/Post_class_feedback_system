<template>
  <section class="page weekly-page">
    <header class="page-head">
      <div>
        <div class="scope-line"><span>高三试点</span><span>周测成绩</span></div>
        <h1>周测成绩与评价</h1>
        <p>查看周测分数与趋势，由班主任和对应学科老师分别记录评价与学习建议。</p>
      </div>
      <div v-if="canManageScores" class="head-actions">
        <el-button type="primary" @click="openBatchDialog"><el-icon><Plus /></el-icon>批量录入</el-button>
        <el-button @click="openSingleDialog"><el-icon><EditPen /></el-icon>单条录入</el-button>
      </div>
    </header>

    <section class="filter-surface">
      <div class="filters">
        <el-select v-model="filters.class_id" placeholder="选择班级" clearable style="width: 180px" @change="load">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filters.subject" placeholder="学科" clearable style="width: 130px" @change="load">
          <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
        </el-select>
        <el-date-picker v-model="filters.start_date" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 160px" @change="load" />
        <el-date-picker v-model="filters.end_date" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 160px" @change="load" />
        <el-input v-model="keyword" placeholder="搜索学生" clearable style="width: 180px" :prefix-icon="Search" />
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      </div>
      <div v-if="summary.length" class="summary-row">
        <span v-for="item in summary" :key="`${item.exam_date}-${item.subject}`" class="summary-chip">
          {{ item.exam_date }} {{ item.subject }} · 均分 {{ item.avg_score }} · 共 {{ item.count }} 人
        </span>
      </div>
    </section>

    <section class="list-surface">
      <el-table v-loading="loading" :data="filteredRows" empty-text="暂无周测成绩" style="width: 100%">
        <el-table-column label="学生 / 班级" min-width="140">
          <template #default="{ row }"><strong>{{ row.student_name || `学生#${row.student_id}` }}</strong><div class="score-secondary">{{ row.class_name }}</div></template>
        </el-table-column>
        <el-table-column prop="subject" label="学科" width="80" />
        <el-table-column label="周测 / 日期" min-width="140">
          <template #default="{ row }">{{ row.exam_name || '周测' }}<div class="score-secondary">{{ row.exam_date }}</div></template>
        </el-table-column>
        <el-table-column label="分数" width="105">
          <template #default="{ row }">{{ row.score }} / {{ row.max_score }}</template>
        </el-table-column>
        <el-table-column prop="rank_in_class" label="排名" width="65">
          <template #default="{ row }">{{ row.rank_in_class || '-' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
        <el-table-column label="教师评价" min-width="290">
          <template #default="{ row }"><WeeklyScoreEvaluations :score="row" @saved="updated => Object.assign(row, updated)" /></template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canManageScores" link type="primary" @click="editRow(row)">编辑</el-button>
            <el-button v-if="canManageScores" link type="danger" @click="removeRow(row)">删除</el-button>
            <el-button link @click="viewTrend(row)">趋势</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 单条录入/编辑 -->
    <el-dialog v-model="singleVisible" :title="editingId ? '编辑成绩' : '单条录入'" width="520px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="班级"><el-select v-model="singleForm.class_id" style="width: 100%" @change="onSingleClassChange"><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
          <el-form-item label="学生"><el-select v-model="singleForm.student_id" filterable style="width: 100%"><el-option v-for="s in singleClassStudents" :key="s.id" :label="s.name" :value="s.id" /></el-select></el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="学科"><el-select v-model="singleForm.subject" style="width: 100%"><el-option v-for="s in subjects" :key="s" :label="s" :value="s" /></el-select></el-form-item>
          <el-form-item label="考试日期"><el-date-picker v-model="singleForm.exam_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        </div>
        <el-form-item label="周次/名称"><el-input v-model="singleForm.exam_name" placeholder="如：第3周周测" /></el-form-item>
        <div class="form-grid">
          <el-form-item label="得分"><el-input-number v-model="singleForm.score" :min="0" :max="singleForm.max_score || 1000" :step="1" style="width: 100%" /></el-form-item>
          <el-form-item label="考试满分（必填）"><el-input-number v-model="singleForm.max_score" :min="1" :max="1000" :step="10" placeholder="请录入满分" style="width: 100%" /></el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="班级排名"><el-input-number v-model="singleForm.rank_in_class" :min="1" :step="1" placeholder="可选" style="width: 100%" /></el-form-item>
          <el-form-item label="备注"><el-input v-model="singleForm.remark" placeholder="可选" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="singleVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitSingle">{{ editingId ? '保存' : '录入' }}</el-button></template>
    </el-dialog>

    <!-- 批量录入 -->
    <el-dialog v-model="batchVisible" title="批量录入周测成绩" width="760px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid-3">
          <el-form-item label="班级"><el-select v-model="batchForm.class_id" style="width: 100%" @change="loadBatchStudents"><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
          <el-form-item label="学科"><el-select v-model="batchForm.subject" style="width: 100%"><el-option v-for="s in subjects" :key="s" :label="s" :value="s" /></el-select></el-form-item>
          <el-form-item label="考试日期"><el-date-picker v-model="batchForm.exam_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="周次/名称"><el-input v-model="batchForm.exam_name" placeholder="如：第5周周测" /></el-form-item>
          <el-form-item label="考试满分（必填）"><el-input-number v-model="batchForm.max_score" :min="1" :max="1000" :step="10" placeholder="请录入满分" style="width: 100%" /></el-form-item>
        </div>
        <div class="batch-note">为下方每名学生填写分数，留空则跳过该生；已存在的同日同科成绩将被覆盖。</div>
        <el-table :data="batchStudents" max-height="360" border>
          <el-table-column label="学生" min-width="160"><template #default="{ row }">{{ row.name }}（{{ row.username }}）</template></el-table-column>
          <el-table-column label="分数" width="160"><template #default="{ row }"><el-input-number v-model="row._score" :min="0" :max="batchForm.max_score" :step="1" controls-position="right" style="width: 130px" placeholder="分数" /></template></el-table-column>
          <el-table-column label="排名" width="120"><template #default="{ row }"><el-input-number v-model="row._rank" :min="1" :step="1" controls-position="right" style="width: 100px" placeholder="可选" /></template></el-table-column>
          <el-table-column label="备注" min-width="140"><template #default="{ row }"><el-input v-model="row._remark" placeholder="可选" /></template></el-table-column>
        </el-table>
      </el-form>
      <template #footer><el-button @click="batchVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitBatch">批量保存</el-button></template>
    </el-dialog>

    <!-- 趋势 -->
    <el-dialog v-model="trendVisible" title="个人趋势" width="640px" destroy-on-close>
      <div v-if="trendData.length" ref="trendChartRef" style="height: 300px"></div>
      <el-empty v-else description="暂无趋势数据" />
      <el-table :data="trendData" style="margin-top: 12px" max-height="260">
        <el-table-column prop="exam_date" label="日期" width="120" />
        <el-table-column prop="exam_name" label="周次" min-width="140" />
        <el-table-column label="分数" width="120"><template #default="{ row }">{{ row.score }} / {{ row.max_score }}</template></el-table-column>
      </el-table>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import WeeklyScoreEvaluations from '../../components/WeeklyScoreEvaluations.vue'
import { useAuthStore } from '../../stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Plus, Refresh, Search } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { listClasses, listStudents } from '../../api/classes'
import { batchCreateWeeklyScores, createWeeklyScore, deleteWeeklyScore, getClassWeeklySummary, getWeeklyTrend, listWeeklyScores, updateWeeklyScore } from '../../api/weeklyScores'

const auth = useAuthStore()
const canManageScores = computed(() => ['admin', 'teacher'].includes(auth.role))
const subjects = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
const classes = ref([])
const rows = ref([])
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const summary = ref([])

const filters = ref({ class_id: null, subject: '', start_date: '', end_date: '' })

const filteredRows = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter(r => `${r.student_name || ''}${r.exam_name || ''}${r.subject}`.toLowerCase().includes(q))
})

const singleVisible = ref(false)
const editingId = ref(null)
const singleClassStudents = ref([])
const singleForm = ref({ class_id: null, student_id: null, subject: '数学', exam_date: new Date().toISOString().slice(0,10), exam_name: '', score: 0, max_score: null, rank_in_class: null, remark: '' })

const batchVisible = ref(false)
const batchForm = ref({ class_id: null, subject: '数学', exam_date: new Date().toISOString().slice(0,10), exam_name: '', max_score: null })
const batchStudents = ref([])

const trendVisible = ref(false)
const trendData = ref([])
const trendChartRef = ref(null)
let chartInstance = null

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.class_id) params.class_id = filters.value.class_id
    if (filters.value.subject) params.subject = filters.value.subject
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    rows.value = await listWeeklyScores(params)
    if (filters.value.class_id) {
      const sParams = { class_id: filters.value.class_id }
      if (filters.value.subject) sParams.subject = filters.value.subject
      summary.value = await getClassWeeklySummary(sParams)
    } else summary.value = []
  } finally { loading.value = false }
}

function todayStr() { return new Date().toISOString().slice(0,10) }

async function openSingleDialog() {
  editingId.value = null
  singleForm.value = { class_id: filters.value.class_id || classes.value[0]?.id || null, student_id: null, subject: filters.value.subject || '数学', exam_date: todayStr(), exam_name: '', score: 0, max_score: null, rank_in_class: null, remark: '' }
  if (singleForm.value.class_id) singleClassStudents.value = await listStudents(singleForm.value.class_id)
  singleVisible.value = true
}

async function onSingleClassChange(cid) {
  singleForm.value.student_id = null
  singleClassStudents.value = cid ? await listStudents(cid) : []
}

async function editRow(row) {
  editingId.value = row.id
  singleForm.value = { class_id: row.class_id, student_id: row.student_id, subject: row.subject, exam_date: row.exam_date, exam_name: row.exam_name, score: row.score, max_score: row.max_score, rank_in_class: row.rank_in_class, remark: row.remark }
  singleClassStudents.value = await listStudents(row.class_id)
  singleVisible.value = true
}

async function submitSingle() {
  if (!singleForm.value.class_id || !singleForm.value.student_id || !singleForm.value.subject || !singleForm.value.exam_date) {
    ElMessage.warning('请完整填写班级、学生、学科和日期')
    return
  }
  if (!singleForm.value.max_score) {
    ElMessage.warning('请填写本次考试满分')
    return
  }
  if (singleForm.value.score > singleForm.value.max_score) {
    ElMessage.warning('得分不能超过满分')
    return
  }
  saving.value = true
  try {
    if (editingId.value) await updateWeeklyScore(editingId.value, singleForm.value)
    else await createWeeklyScore(singleForm.value)
    ElMessage.success(editingId.value ? '已更新' : '已录入')
    singleVisible.value = false
    await load()
  } finally { saving.value = false }
}

async function removeRow(row) {
  await ElMessageBox.confirm(`确认删除 ${row.student_name || row.student_id} 的 ${row.subject} ${row.exam_date} 成绩？`, '删除确认', { type: 'warning' })
  await deleteWeeklyScore(row.id)
  ElMessage.success('已删除')
  await load()
}

async function openBatchDialog() {
  batchForm.value = { class_id: filters.value.class_id || classes.value[0]?.id || null, subject: filters.value.subject || '数学', exam_date: todayStr(), exam_name: '', max_score: null }
  batchStudents.value = []
  if (batchForm.value.class_id) await loadBatchStudents()
  batchVisible.value = true
}

async function loadBatchStudents() {
  if (!batchForm.value.class_id) { batchStudents.value = []; return }
  const list = await listStudents(batchForm.value.class_id)
  batchStudents.value = list.map(s => ({ ...s, _score: null, _rank: null, _remark: '' }))
}

async function submitBatch() {
  if (!batchForm.value.class_id || !batchForm.value.subject || !batchForm.value.exam_date) {
    ElMessage.warning('请选择班级、学科和日期')
    return
  }
  if (!batchForm.value.max_score) {
    ElMessage.warning('请填写本次考试满分')
    return
  }
  const records = batchStudents.value
    .filter(s => s._score !== null && s._score !== '' && s._score !== undefined)
    .map(s => ({ student_id: s.id, score: Number(s._score), rank_in_class: s._rank || null, remark: s._remark || '' }))
  if (!records.length) { ElMessage.warning('请至少为一名学生填写分数'); return }
  saving.value = true
  try {
    await batchCreateWeeklyScores({ ...batchForm.value, records })
    ElMessage.success(`已批量保存 ${records.length} 条`)
    batchVisible.value = false
    await load()
  } finally { saving.value = false }
}

async function viewTrend(row) {
  trendData.value = await getWeeklyTrend({ student_id: row.student_id, subject: row.subject })
  trendVisible.value = true
  await nextTick()
  if (trendChartRef.value && trendData.value.length) {
    if (chartInstance) chartInstance.dispose()
    chartInstance = echarts.init(trendChartRef.value)
    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: trendData.value.map(d => d.exam_date) },
      yAxis: { type: 'value', name: '分数' },
      series: [{ type: 'line', smooth: true, data: trendData.value.map(d => d.score), areaStyle: {}, markLine: { data: [{ type: 'average', name: '平均分' }] } }],
      grid: { left: 40, right: 20, top: 20, bottom: 30 }
    })
  }
}

watch(trendVisible, (v) => { if (!v && chartInstance) { chartInstance.dispose(); chartInstance = null } })

import { onMounted } from 'vue'
onMounted(async () => {
  classes.value = await listClasses()
  // 默认选中第一个高三班级
  const g3 = classes.value.find(c => c.grade === '高三') || classes.value[0]
  if (g3) filters.value.class_id = g3.id
  await load()
})
</script>

<style scoped>
.score-secondary { color: var(--ink-muted); font-size: 12px; line-height: 1.6; }
.weekly-page {
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
  font-size: 13.5px;
  color: #64748b;
}

.head-actions {
  display: flex;
  gap: 10px;
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

.summary-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.summary-chip {
  padding: 3px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
  color: #334155;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
}

.batch-note {
  color: #64748b;
  font-size: 12px;
  margin: 6px 0 10px;
}

@media (max-width: 760px) {
  .page-head {
    flex-direction: column;
  }
  .form-grid, .form-grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>
