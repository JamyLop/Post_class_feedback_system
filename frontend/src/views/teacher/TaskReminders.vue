<template>
  <section class="page remind-page">
    <header class="page-head">
      <div>
        <div class="scope-line"><span>高三试点</span><span>任务提醒 · 每日记录</span></div>
        <h1>任务提醒中心</h1>
        <p>汇总所带班级的学生任务安排与执行情况：逾期任务、今日到期、今日未打卡，并在此完成阶段任务的每日记录，记录自动折算积分。</p>
      </div>
      <div class="head-actions">
        <el-button type="primary" :disabled="!batchRows.length" @click="batchVisible = true"><el-icon><EditPen /></el-icon>每日记录（{{ batchRows.length }}）</el-button>
      </div>
    </header>

    <section class="filter-surface">
      <div class="filters">
        <el-select v-model="filters.class_id" placeholder="全部所带班级" clearable style="width: 200px" @change="load">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        <span class="date-tag">{{ data.date }} · 数据截至今日</span>
      </div>
      <div class="count-row">
        <div class="count-card is-danger"><strong>{{ data.counts.overdue || 0 }}</strong><span>逾期任务</span></div>
        <div class="count-card is-warning"><strong>{{ data.counts.due_today || 0 }}</strong><span>今日到期</span></div>
        <div class="count-card is-info"><strong>{{ data.counts.unlogged_today || 0 }}</strong><span>今日未打卡</span></div>
        <el-button link type="primary" :disabled="!data.unlogged_today.length" @click="addAllUnlogged">全部未打卡加入今日记录</el-button>
      </div>
    </section>

    <section class="list-surface">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="`逾期任务（${data.overdue.length}）`" name="overdue">
          <el-table :data="data.overdue" empty-text="暂无逾期任务">
            <el-table-column label="学生" min-width="130"><template #default="{ row }"><strong>{{ row.student_name }}</strong><div class="sub">{{ row.class_name }}</div></template></el-table-column>
            <el-table-column label="任务" min-width="200" show-overflow-tooltip><template #default="{ row }">{{ row.title }}<div class="sub">V{{ row.version }}阶段</div></template></el-table-column>
            <el-table-column label="学科/周期" width="130"><template #default="{ row }">{{ row.subject || '-' }} · {{ cadenceText(row.cadence) }}</template></el-table-column>
            <el-table-column prop="due_on" label="截止" width="120" />
            <el-table-column label="积分" width="80"><template #default="{ row }">{{ row.points }}分</template></el-table-column>
            <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag type="danger">逾期{{ row.overdue_days }}天</el-tag></template></el-table-column>
            <el-table-column label="操作" width="170" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openCase(row)">去档案</el-button><el-button link @click="addToBatch(row)">记今日</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`今日到期（${data.due_today.length}）`" name="due">
          <el-table :data="data.due_today" empty-text="今日无到期任务">
            <el-table-column label="学生" min-width="130"><template #default="{ row }"><strong>{{ row.student_name }}</strong><div class="sub">{{ row.class_name }}</div></template></el-table-column>
            <el-table-column label="任务" min-width="200" show-overflow-tooltip><template #default="{ row }">{{ row.title }}<div class="sub">V{{ row.version }}阶段</div></template></el-table-column>
            <el-table-column label="学科/周期" width="130"><template #default="{ row }">{{ row.subject || '-' }} · {{ cadenceText(row.cadence) }}</template></el-table-column>
            <el-table-column label="积分" width="80"><template #default="{ row }">{{ row.points }}分</template></el-table-column>
            <el-table-column label="今日记录" width="110"><template #default="{ row }"><el-tag :type="row.logged_today ? 'success' : 'info'">{{ row.logged_today ? '已记' : '未记' }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="170" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openCase(row)">去档案</el-button><el-button link @click="addToBatch(row)">记今日</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`今日未打卡（${data.unlogged_today.length}）`" name="unlogged">
          <el-table :data="data.unlogged_today" empty-text="今日执行均已记录">
            <el-table-column label="学生" min-width="130"><template #default="{ row }"><strong>{{ row.student_name }}</strong><div class="sub">{{ row.class_name }}</div></template></el-table-column>
            <el-table-column label="任务" min-width="200" show-overflow-tooltip><template #default="{ row }">{{ row.title }}<div class="sub">V{{ row.version }}阶段</div></template></el-table-column>
            <el-table-column label="学科/周期" width="130"><template #default="{ row }">{{ row.subject || '-' }} · {{ cadenceText(row.cadence) }}</template></el-table-column>
            <el-table-column prop="due_on" label="截止" width="120" />
            <el-table-column label="积分" width="80"><template #default="{ row }">{{ row.points }}分</template></el-table-column>
            <el-table-column label="操作" width="170" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openCase(row)">去档案</el-button><el-button link @click="addToBatch(row)">记今日</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="batchVisible" title="阶段任务每日记录" width="760px" destroy-on-close>
      <div class="batch-note">一次提交多任务当天的执行情况；得分 = 满分积分 × 完成度，提交后自动重算各学生当前阶段完成度。</div>
      <el-form label-position="top">
        <el-form-item label="记录日期"><el-date-picker v-model="logDate" type="date" value-format="YYYY-MM-DD" style="width: 220px" /></el-form-item>
      </el-form>
      <el-table :data="batchRows" max-height="360" border empty-text="暂无待记录任务，可从上方列表加入">
        <el-table-column label="学生" min-width="110"><template #default="{ row }">{{ row.student_name }}</template></el-table-column>
        <el-table-column label="任务" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ row.title }}（{{ row.points }}分）</template></el-table-column>
        <el-table-column label="完成度" width="150"><template #default="{ row }"><el-input-number v-model="row.completion_rate" :min="0" :max="100" :step="10" controls-position="right" style="width: 120px" /></template></el-table-column>
        <el-table-column label="记录" min-width="160"><template #default="{ row }"><el-input v-model="row.self_check" placeholder="执行情况说明（可选）" /></template></el-table-column>
        <el-table-column label="预计得分" width="100"><template #default="{ row }">{{ expectedPoints(row) }}</template></el-table-column>
        <el-table-column label="操作" width="80"><template #default="{ $index }"><el-button link type="danger" @click="batchRows.splice($index, 1)">移除</el-button></template></el-table-column>
      </el-table>
      <template #footer><el-button @click="batchVisible = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!batchRows.length" @click="submitBatch">提交每日记录</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { EditPen, Refresh } from '@element-plus/icons-vue'
import { batchCheckinTasks, getTaskReminders } from '../../api/studentCases'
import { listClasses } from '../../api/classes'

const router = useRouter()
const classes = ref([])
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('overdue')
const filters = ref({ class_id: null })
const data = ref({ date: '', overdue: [], due_today: [], unlogged_today: [], counts: {} })
const batchVisible = ref(false)
const logDate = ref(new Date().toISOString().slice(0, 10))
const batchRows = ref([])

const cadenceText = (c) => ({ daily: '日计划', weekly: '周计划', monthly: '月计划' }[c] || c || '-')
const expectedPoints = (row) => Math.round(((row.points || 0) * (row.completion_rate || 0) / 100) * 100) / 100

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.class_id) params.class_id = filters.value.class_id
    data.value = await getTaskReminders(params)
  } finally { loading.value = false }
}

function openCase(row) {
  router.push(`/teacher/student-cases/${row.case_id}`)
}

function addToBatch(row) {
  if (batchRows.value.some(r => r.task_id === row.task_id)) {
    ElMessage.warning('该任务已在今日记录中')
    return
  }
  batchRows.value.push({ task_id: row.task_id, title: row.title, student_name: row.student_name, points: row.points, completion_rate: 100, self_check: '' })
  ElMessage.success(`已加入：${row.title}`)
}

function addAllUnlogged() {
  let added = 0
  for (const row of data.value.unlogged_today) {
    if (!batchRows.value.some(r => r.task_id === row.task_id)) {
      batchRows.value.push({ task_id: row.task_id, title: row.title, student_name: row.student_name, points: row.points, completion_rate: 100, self_check: '' })
      added += 1
    }
  }
  if (!added) ElMessage.warning('未打卡任务均已加入')
  else batchVisible.value = true
}

async function submitBatch() {
  if (!batchRows.value.length) return
  saving.value = true
  try {
    await batchCheckinTasks({
      log_date: logDate.value || new Date().toISOString().slice(0, 10),
      items: batchRows.value.map(r => ({ task_id: r.task_id, completion_rate: Number(r.completion_rate) || 0, self_check: r.self_check || '' })),
    })
    ElMessage.success(`已提交 ${batchRows.value.length} 条每日记录，积分与阶段完成度已更新`)
    batchRows.value = []
    batchVisible.value = false
    await load()
  } finally { saving.value = false }
}

onMounted(async () => {
  classes.value = await listClasses()
  await load()
})
</script>

<style scoped>
.remind-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.scope-line { display: flex; gap: 8px; margin-bottom: 8px; }
.scope-line span { font-size: 11px; font-weight: 600; color: #2f5bff; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 8px; border-radius: 6px; }
.scope-line span + span { color: #64748b; background: #ffffff; border-color: #e2e8f0; }
.page-head h1 { margin: 0 0 6px; font-size: 24px; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; }
.page-head p { margin: 0; font-size: 13.5px; color: #64748b; max-width: 76ch; line-height: 1.5; }
.head-actions { display: flex; gap: 10px; }
.filter-surface, .list-surface { background: #ffffff; border: 1px solid #e2e8f0; border-radius: var(--radius); padding: 16px 18px; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.date-tag { color: #94a3b8; font-size: 12px; margin-left: auto; }
.count-row { display: flex; gap: 12px; align-items: center; margin-top: 14px; padding-top: 14px; border-top: 1px solid #f1f5f9; flex-wrap: wrap; }
.count-card { display: flex; align-items: baseline; gap: 8px; padding: 10px 16px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; }
.count-card strong { font-size: 22px; font-weight: 700; }
.count-card span { font-size: 12px; color: #64748b; }
.count-card.is-danger strong { color: #dc2626; }
.count-card.is-warning strong { color: #d97706; }
.count-card.is-info strong { color: #2563eb; }
.batch-note { color: #64748b; font-size: 12.5px; margin-bottom: 12px; }
.sub { color: #94a3b8; font-size: 12px; font-weight: 400; }
@media (max-width: 760px) { .page-head { flex-direction: column; } }
</style>
