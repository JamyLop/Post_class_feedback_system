<template>
  <section class="page supervision-page">
    <header class="page-head">
      <div>
        <div class="scope-badges">
          <span class="badge-tag">校级决策与督导</span>
          <span class="badge-sub">全校学情驾驶舱</span>
        </div>
        <h1>督查驾驶舱</h1>
        <p>覆盖全学段、全年级，重点关注方案待确认、逾期任务、长期未督查和待复盘学生，为学校管理提供数据支撑。</p>
      </div>
    </header>

    <div class="metrics-grid">
      <div v-for="item in cards" :key="item.key" class="metric-card" :class="item.tone">
        <div class="metric-header">
          <span class="metric-dot"></span>
          <span class="metric-label">{{ item.label }}</span>
        </div>
        <div class="metric-num">{{ displayProgress[item.key] }}</div>
      </div>
    </div>

    <!-- 筛选 + 分布 -->
    <div class="panel-row">
      <div class="filter-card">
        <div class="filter-head">
          <span class="filter-title">筛选</span>
          <el-button link size="small" @click="resetFilters">重置</el-button>
        </div>
        <div class="filter-grid">
          <el-select v-model="filterStage" placeholder="学段" clearable size="small" style="width: 100%">
            <el-option v-for="s in stageOptions" :key="s" :label="s" :value="s" />
          </el-select>
          <el-select v-model="filterGrade" placeholder="年级" clearable size="small" style="width: 100%">
            <el-option v-for="g in gradeOptions" :key="g" :label="g" :value="g" />
          </el-select>
          <el-select v-model="filterClassId" placeholder="班级" clearable size="small" style="width: 100%">
            <el-option v-for="c in filteredClassOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 100%">
            <el-option v-for="(label, val) in statuses" :key="val" :label="label" :value="val" />
          </el-select>
        </div>
        <div class="filter-foot">
          <el-input v-model="keyword" placeholder="搜索学生/班级/目标" clearable size="small" />
          <span class="filter-count">已筛选 {{ filteredRows.length }} / {{ rows.length }}</span>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-head">年级分布 <small>{{ filteredRows.length }} 份档案</small></div>
        <EChart :option="gradeChartOption" height="220px" />
      </div>

      <div class="chart-card">
        <div class="chart-head">状态分布</div>
        <EChart :option="statusChartOption" height="220px" />
      </div>
    </div>

    <div class="table-container">
      <div class="table-head">
        <div>
          <h2>学生总案监控表</h2>
          <span class="count-tag">实时数据 · 全学段</span>
        </div>
        <el-button :loading="loading" @click="load">刷新数据</el-button>
      </div>

      <el-table v-loading="loading" :data="filteredRows" empty-text="尚无学生档案数据" class="supervision-table" row-class-name="is-clickable" @row-click="goDetail">
        <el-table-column prop="student_name" label="学生姓名" min-width="110" />
        <el-table-column label="学段 / 年级" min-width="130">
          <template #default="{ row }">
            <span class="cell-sub">{{ classMeta(row.class_id).label }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="所属班级" min-width="130" />
        <el-table-column prop="admission_target" label="升学目标" min-width="260" show-overflow-tooltip />
        <el-table-column label="当前状态" width="130">
          <template #default="{ row }">
            <span class="badge-status" :class="`is-${row.status}`">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80">
          <template #default="{ row }">
            <span class="version-tag">V{{ row.version }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="goDetail(row)">查看档案</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'
import { listClasses } from '../../api/classes'
import EChart from '../../components/EChart.vue'

const router = useRouter()
function goDetail(row) {
  if (!row?.id) return
  router.push(`/admin/cases/${row.id}`)
}

const loading = ref(false), rows = ref([]), progress = ref({}), classes = ref([])
const filterStage = ref('')
const filterGrade = ref('')
const filterClassId = ref(null)
const filterStatus = ref('')
const keyword = ref('')

const cards = computed(() => [
  { key: 'total', label: '总案数', tone: 'tone-primary' },
  { key: 'pending_confirmation', label: '待德育审查', tone: 'tone-amber' },
  { key: 'revision_required', label: '待班主任整改', tone: 'tone-red' },
  { key: 'overdue_tasks', label: '任务逾期数', tone: 'tone-red' },
  { key: 'long_unreviewed', label: '长期未督查', tone: 'tone-red' },
  { key: 'pending_review', label: '待复盘学生', tone: 'tone-blue' },
  { key: 'executing', label: '正常执行中', tone: 'tone-green' },
])

const statuses = {
  draft: '草稿',
  pending_confirmation: '待德育审查',
  revision_required: '待班主任整改',
  executing: '执行中',
  pending_review: '待复盘',
  adjusted: '已调整',
  archived: '已归档',
}
const statusLabel = (val) => statuses[val] || val

// 当有筛选时，卡片显示按筛选结果重算（除逾期/长期未督查保持全局）
const displayProgress = computed(() => {
  const hasFilter = filterStage.value || filterGrade.value || filterClassId.value || filterStatus.value || keyword.value.trim()
  if (!hasFilter) return progress.value
  const counts = { total: filteredRows.value.length, pending_confirmation: 0, revision_required: 0, pending_review: 0, executing: 0, draft: 0, adjusted: 0, archived: 0 }
  for (const r of filteredRows.value) {
    if (counts[r.status] !== undefined) counts[r.status]++
  }
  return { ...progress.value, ...counts, total: filteredRows.value.length }
})

const classMap = computed(() => {
  const m = new Map()
  for (const c of classes.value) m.set(c.id, c)
  return m
})
const classMeta = (classId) => {
  const c = classMap.value.get(classId)
  if (!c) return { label: '-', stage: '', grade: '' }
  const stage = c.education_stage || ''
  const grade = c.grade || ''
  return { label: [stage, grade].filter(Boolean).join(' · ') || '-', stage, grade }
}

const stageOptions = computed(() => {
  const s = new Set(classes.value.map(c => c.education_stage).filter(Boolean))
  return Array.from(s)
})
const gradeOptions = computed(() => {
  let list = classes.value
  if (filterStage.value) list = list.filter(c => c.education_stage === filterStage.value)
  const g = new Set(list.map(c => c.grade).filter(Boolean))
  return Array.from(g)
})
const filteredClassOptions = computed(() => {
  let list = classes.value
  if (filterStage.value) list = list.filter(c => c.education_stage === filterStage.value)
  if (filterGrade.value) list = list.filter(c => c.grade === filterGrade.value)
  return list
})

watch(filterStage, () => { filterGrade.value = ''; filterClassId.value = null })
watch(filterGrade, () => { filterClassId.value = null })

const filteredRows = computed(() => {
  let list = rows.value
  if (filterClassId.value) {
    list = list.filter(r => r.class_id === filterClassId.value)
  } else {
    if (filterStage.value) {
      const ids = new Set(classes.value.filter(c => c.education_stage === filterStage.value).map(c => c.id))
      list = list.filter(r => ids.has(r.class_id))
    }
    if (filterGrade.value) {
      const ids = new Set(classes.value.filter(c => c.grade === filterGrade.value).map(c => c.id))
      list = list.filter(r => ids.has(r.class_id))
    }
  }
  if (filterStatus.value) list = list.filter(r => r.status === filterStatus.value)
  const kw = keyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(r => {
      const meta = classMeta(r.class_id)
      return [r.student_name, r.class_name, meta.label, r.admission_target, r.status].join(' ').toLowerCase().includes(kw)
    })
  }
  return list
})

const gradeChartOption = computed(() => {
  const counter = new Map()
  for (const r of filteredRows.value) {
    const meta = classMeta(r.class_id)
    const k = meta.label || '未分班'
    counter.set(k, (counter.get(k) || 0) + 1)
  }
  const data = Array.from(counter.entries()).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 10)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 12, right: 12, top: 8, bottom: 24, containLabel: true },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: data.map(d => d.name), axisLabel: { width: 90, overflow: 'truncate' } },
    color: ['#3b82f6'],
    series: [{ type: 'bar', barMaxWidth: 22, itemStyle: { borderRadius: [0, 6, 6, 0] }, data: data.map(d => d.value) }],
  }
})

const statusChartOption = computed(() => {
  const keys = ['draft', 'pending_confirmation', 'revision_required', 'executing', 'pending_review', 'adjusted', 'archived']
  const counts = {}
  for (const k of keys) counts[k] = 0
  for (const r of filteredRows.value) if (counts[r.status] !== undefined) counts[r.status]++
  return {
    tooltip: { trigger: 'item' },
    color: ['#94a3b8', '#f59e0b', '#ef4444', '#10b981', '#3b82f6', '#8b5cf6', '#6b7280'],
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true } },
      data: keys.map(k => ({ value: counts[k], name: statuses[k] })).filter(d => d.value > 0),
    }],
  }
})

function resetFilters() {
  filterStage.value = ''
  filterGrade.value = ''
  filterClassId.value = null
  filterStatus.value = ''
  keyword.value = ''
}

async function load() {
  loading.value = true
  try {
    const [prog, list, cls] = await Promise.all([getCaseProgress(), listStudentCases(), listClasses().catch(() => [])])
    progress.value = prog || {}
    rows.value = Array.isArray(list) ? list : []
    classes.value = Array.isArray(cls) ? cls : []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.supervision-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.scope-badges {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.badge-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 6px;
}

.badge-sub {
  font-size: 11px;
  color: #64748b;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 6px;
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
}

.metric-card {
  padding: 16px 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.metric-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #94a3b8;
}

.metric-card.tone-primary .metric-dot { background: #2f5bff; }
.metric-card.tone-amber .metric-dot { background: #d97706; }
.metric-card.tone-red .metric-dot { background: #dc2626; }
.metric-card.tone-blue .metric-dot { background: #3b82f6; }
.metric-card.tone-green .metric-dot { background: #059669; }

.metric-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
}

.metric-num {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.metric-card.tone-red .metric-num { color: #dc2626; }

.panel-row {
  display: grid;
  grid-template-columns: 340px 1fr 1fr;
  gap: 12px;
}

.filter-card, .chart-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  padding: 14px 16px;
}

.filter-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.filter-title { font-size: 13px; font-weight: 600; color: var(--ink); }
.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.filter-foot {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-count { font-size: 11px; color: #94a3b8; }

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}
.chart-head small { font-weight: 400; font-size: 11px; color: #94a3b8; }

.cell-sub { font-size: 12px; color: #64748b; }

.table-container {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  overflow: hidden;
}

.table-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.table-head > div {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.count-tag {
  font-size: 11.5px;
  color: #64748b;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 2px 7px;
  border-radius: 6px;
}

.version-tag {
  font-size: 12px;
  color: #475569;
  font-family: monospace;
}

.badge-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}
.badge-status.is-executing { background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
.badge-status.is-pending_review { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
.badge-status.is-pending_confirmation { background: #fffbeb; border-color: #fde68a; color: #92400e; }
.badge-status.is-revision_required { background: #fef2f2; border-color: #fecaca; color: #991b1b; }

:deep(.supervision-table .el-table__row.is-clickable) { cursor: pointer; }
:deep(.supervision-table .el-table__row.is-clickable:hover) { background: #f8fafc; }

@media (max-width: 1200px) {
  .metrics-grid { grid-template-columns: repeat(4, 1fr); }
  .panel-row { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
