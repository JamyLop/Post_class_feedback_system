<template>
  <section class="page points-page">
    <header class="page-head">
      <div>
        <div class="scope-line"><span>高三试点</span><span>积分周报 · 月报</span></div>
        <h1>积分周报月报</h1>
        <p>班主任完成阶段任务每日记录后，系统按“满分积分 × 完成度”从每名学生处累加积分，在此一键生成并查看班级周报、月报。</p>
      </div>
      <div class="head-actions">
        <el-button type="primary" :loading="building" :disabled="!filters.class_id" @click="build"><el-icon><Plus /></el-icon>一键生成本班报表</el-button>
      </div>
    </header>

    <section class="filter-surface">
      <div class="filters">
        <el-select v-model="filters.class_id" placeholder="选择班级" style="width: 200px" @change="load">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filters.period_type" style="width: 130px" @change="onTypeChange">
          <el-option label="周报" value="weekly" />
          <el-option label="月报" value="monthly" />
        </el-select>
        <el-input v-if="filters.period_type === 'weekly'" v-model="filters.period_label" placeholder="如 2026-W36" style="width: 150px" @change="load" />
        <el-date-picker v-else v-model="filters.period_label" type="month" placeholder="月份" value-format="YYYY-MM" style="width: 160px" @change="load" />
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      </div>
      <div v-if="rows.length" class="summary-row">
        <span class="summary-chip">共 {{ rows.length }} 人</span>
        <span class="summary-chip">班均 {{ avgPoints }} 分</span>
        <span class="summary-chip">最高 {{ maxPoints }} 分（{{ topStudent }}）</span>
        <span class="summary-chip">周期 {{ periodRange }}</span>
      </div>
    </section>

    <section class="list-surface">
      <el-table v-loading="loading" :data="rows" empty-text="暂无积分报表，请先选择班级与周期，必要时点击“一键生成本班报表”">
        <el-table-column label="学生" min-width="130"><template #default="{ row }"><strong>{{ row.student_name || `学生#${row.student_id}` }}</strong></template></el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column prop="period_label" label="周期" width="120" />
        <el-table-column label="任务/打卡" width="120"><template #default="{ row }">{{ row.task_count }} / {{ row.checkin_count }}</template></el-table-column>
        <el-table-column label="获得积分" width="130" sortable prop="earned_points"><template #default="{ row }"><strong>{{ row.earned_points }}</strong> / {{ row.total_points }}</template></el-table-column>
        <el-table-column label="完成率" min-width="180"><template #default="{ row }"><el-progress :percentage="Number(row.completion_rate) || 0" :stroke-width="8" /></template></el-table-column>
      </el-table>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { listClasses } from '../../api/classes'
import { buildPointsReports, listPointsReports } from '../../api/pointsReports'

const classes = ref([])
const rows = ref([])
const loading = ref(false)
const building = ref(false)
const filters = ref({ class_id: null, period_type: 'weekly', period_label: '' })

function currentWeekLabel() {
  const now = new Date()
  const thursday = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))
  const day = (thursday.getUTCDay() + 6) % 7
  thursday.setUTCDate(thursday.getUTCDate() - day + 3)
  const firstThursday = new Date(Date.UTC(thursday.getUTCFullYear(), 0, 4))
  const week = 1 + Math.round(((thursday - firstThursday) / 86400000 - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7)
  return `${thursday.getUTCFullYear()}-W${String(week).padStart(2, '0')}`
}
function currentMonthLabel() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

const avgPoints = computed(() => {
  if (!rows.value.length) return 0
  return Math.round((rows.value.reduce((s, r) => s + (Number(r.earned_points) || 0), 0) / rows.value.length) * 100) / 100
})
const maxPoints = computed(() => rows.value.length ? Math.max(...rows.value.map(r => Number(r.earned_points) || 0)) : 0)
const topStudent = computed(() => rows.value.find(r => (Number(r.earned_points) || 0) === maxPoints.value)?.student_name || '-')
const periodRange = computed(() => {
  const first = rows.value[0]
  return first ? `${first.period_start} ~ ${first.period_end}` : '-'
})

function onTypeChange() {
  filters.value.period_label = filters.value.period_type === 'weekly' ? currentWeekLabel() : currentMonthLabel()
  load()
}

async function load() {
  if (!filters.value.class_id) { rows.value = []; return }
  loading.value = true
  try {
    rows.value = await listPointsReports({
      class_id: filters.value.class_id,
      period_type: filters.value.period_type,
      period_label: filters.value.period_label || undefined,
    })
  } finally { loading.value = false }
}

async function build() {
  if (!filters.value.class_id) { ElMessage.warning('请先选择班级'); return }
  building.value = true
  try {
    rows.value = await buildPointsReports({
      class_id: filters.value.class_id,
      period_type: filters.value.period_type,
      period_label: filters.value.period_label || undefined,
    })
    ElMessage.success(`已生成 ${rows.value.length} 名学生的${filters.value.period_type === 'weekly' ? '周报' : '月报'}`)
  } finally { building.value = false }
}

onMounted(async () => {
  classes.value = await listClasses()
  filters.value.period_label = currentWeekLabel()
  const g3 = classes.value.find(c => c.grade === '高三') || classes.value[0]
  if (g3) filters.value.class_id = g3.id
  await load()
})
</script>

<style scoped>
.points-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.scope-line { display: flex; gap: 8px; margin-bottom: 8px; }
.scope-line span { font-size: 11px; font-weight: 600; color: #2f5bff; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 8px; border-radius: 6px; }
.scope-line span + span { color: #64748b; background: #ffffff; border-color: #e2e8f0; }
.page-head h1 { margin: 0 0 6px; font-size: 24px; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; }
.page-head p { margin: 0; font-size: 13.5px; color: #64748b; max-width: 76ch; line-height: 1.5; }
.head-actions { display: flex; gap: 10px; }
.filter-surface, .list-surface { background: #ffffff; border: 1px solid #e2e8f0; border-radius: var(--radius); padding: 16px 18px; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.summary-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; padding-top: 12px; border-top: 1px solid #f1f5f9; }
.summary-chip { padding: 3px 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px; color: #334155; }
@media (max-width: 760px) { .page-head { flex-direction: column; } }
</style>
