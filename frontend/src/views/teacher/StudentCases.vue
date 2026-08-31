<template>
  <section class="page cases-page">
    <header class="page-head">
      <div class="head-info">
        <span class="overline">2026-2027学年</span>
        <h1>学生档案</h1>
        <p>跟进每位学生的总案状态与阶段任务，落实一生一策。</p>
      </div>
      <el-button v-if="auth.role === 'teacher'" type="primary" @click="openCreate">
        新建档案
      </el-button>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card total-card">
        <span class="kpi-label">总案数</span>
        <div class="kpi-num">{{ progress.total || 0 }}</div>
        <span class="kpi-sub">已建档</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">待核对</span>
        <div class="kpi-num">{{ progress.draft || 0 }}</div>
        <span class="kpi-sub">草稿待完善</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">待确认</span>
        <div class="kpi-num">{{ progress.pending_confirmation || 0 }}</div>
        <span class="kpi-sub">待核准</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">执行中</span>
        <div class="kpi-num">{{ progress.executing || 0 }}</div>
        <span class="kpi-sub">进行中</span>
      </div>
      <div class="kpi-card is-warn">
        <span class="kpi-label">逾期任务</span>
        <div class="kpi-num is-danger">{{ progress.overdue_tasks || 0 }}</div>
        <span class="kpi-sub">需跟进</span>
      </div>
    </div>

    <!-- 列表区域 -->
    <div class="list-container">
      <div class="list-toolbar">
        <div class="toolbar-left">
          <h2>学生档案列表</h2>
          <span class="count-tag">共 {{ filteredRows.length }} 人</span>
        </div>
        <div class="filters">
          <el-select v-model="workFilter" style="width: 120px" @change="applyWorkFilter">
            <el-option label="全部档案" value="all" />
            <el-option label="待处理" value="todo" />
            <el-option label="执行中" value="executing" />
          </el-select>
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索学生或班级"
            :prefix-icon="Search"
            style="width: 200px"
          />
          <el-select
            v-model="status"
            clearable
            placeholder="全部状态"
            style="width: 130px"
            @change="onStatusChange"
          >
            <el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredRows"
        empty-text="暂无符合条件的学生总案"
        class="cases-table"
        @row-click="openCase"
      >
        <el-table-column label="学生姓名" min-width="160">
          <template #default="{ row }">
            <div class="student-cell">
              <span class="student-avatar">{{ row.student_name?.slice(0, 1) || '学' }}</span>
              <div class="student-info">
                <strong>{{ row.student_name }}</strong>
                <small>档案号 #{{ row.id }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="所属班级" min-width="140" />
        <el-table-column prop="admission_target" label="升学目标" min-width="240" show-overflow-tooltip />
        <el-table-column prop="current_summary" label="当前学情进展" min-width="240" show-overflow-tooltip />
        <el-table-column label="方案状态" width="130">
          <template #default="{ row }">
            <span class="badge-status" :class="`is-${row.status}`">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="版本" width="90">
          <template #default="{ row }">
            <span class="version-tag">V{{ row.version }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openCase(row)">查看档案</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建总案弹窗 -->
    <el-dialog v-model="createVisible" title="新建学生总案" width="600px" destroy-on-close>
      <el-form label-position="top">
        <div class="create-grid">
          <el-form-item label="学年">
            <el-select v-model="createForm.cycle_id" placeholder="选择学年" filterable style="width:100%">
              <el-option v-for="item in cycleOptions" :key="item.id" :label="cycleLabel(item)" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="班级">
            <el-select v-model="createForm.class_id" placeholder="选择班级" empty-text="暂无班级，请先在班级管理创建班级" @change="loadClassStudents">
              <el-option v-for="item in availableClasses" :key="item.id" :label="`${item.name}（${item.grade}·${item.school_year}）`" :value="item.id" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="学生">
          <el-select v-model="createForm.student_id" filterable placeholder="选择尚未建档的学生">
            <el-option
              v-for="item in availableStudents"
              :key="item.id"
              :label="`${item.name}（${item.username}）${classStudentIds.has(item.id) ? '' : ' · 创建时加入班级'}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="家长评价">
          <el-input
            v-model="createForm.parent_evaluation"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 8 }"
            placeholder="记录家长对学生的评价、关注点或家校协同建议"
          />
        </el-form-item>
        <el-form-item label="主要需求">
          <el-input
            v-model="createForm.primary_needs"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="例如：学生主要需求、期望支持方向或家校配合事项"
          />
        </el-form-item>
        <el-form-item label="当前状态说明">
          <el-input
            v-model="createForm.current_summary"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="例如：班主任手工建档，待完善学科方案"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建并进入档案</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { addStudents, listClasses, listStudents } from '../../api/classes'
import { createCaseCycle, createStudentCase, getCaseProgress, listCaseCycles, listStudentCases } from '../../api/studentCases'
import { listUsers } from '../../api/users'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const rows = ref([]), loading = ref(false), status = ref(''), keyword = ref('')
const workFilter = ref('all')
const cycles = ref([]), classes = ref([]), classStudents = ref([]), allStudents = ref([])
const createVisible = ref(false), creating = ref(false)
const createForm = reactive({ cycle_id: null, class_id: null, student_id: null, parent_evaluation: '', primary_needs: '', current_summary: '' })
const progress = ref({ total: 0, draft: 0, pending_confirmation: 0, revision_required: 0, executing: 0, overdue_tasks: 0 })
const statuses = [
  ['draft', '草稿'],
  ['pending_confirmation', '待德育审查'],
  ['revision_required', '待班主任整改'],
  ['executing', '执行中'],
  ['pending_review', '待复盘'],
  ['adjusted', '已调整'],
  ['archived', '已归档'],
].map(([value, label]) => ({ value, label }))

const statusLabel = (value) => statuses.find((item) => item.value === value)?.label || value
const cycleLabel = (item) => {
  if (!item) return ''
  if (item.school_year) return `${item.school_year}学年`
  return (item.name || '').replace('高三备考周期', '学年').replace('备考周期', '学年')
}
// 与班级管理保持一致的学年范围：2020-2021 至 2100-2101
const schoolYears = Array.from({ length: 81 }, (_, i) => {
  const start = 2020 + i
  return `${start}-${start + 1}`
})
const cycleOptions = computed(() => {
  const byYear = new Map(cycles.value.map((c) => [c.school_year, c]))
  return schoolYears.map((year) => {
    const existing = byYear.get(year)
    if (existing) return existing
    return { id: year, school_year: year, name: `${year}学年`, is_active: false, _virtual: true }
  })
})

const filteredRows = computed(() => {
  let result = rows.value
  if (workFilter.value === 'todo') {
    result = result.filter((row) => ['draft', 'revision_required', 'pending_review'].includes(row.status))
  }
  if (workFilter.value === 'executing') {
    result = result.filter((row) => ['executing', 'adjusted'].includes(row.status))
  }
  const query = keyword.value.trim().toLowerCase()
  if (query) {
    result = result.filter((row) => `${row.student_name || ''}${row.class_name || ''}`.toLowerCase().includes(query))
  }
  return result
})

const availableClasses = computed(() => classes.value)
// 兼容旧命名，保留 high3Classes 供遗留逻辑引用
const high3Classes = availableClasses
const classStudentIds = computed(() => new Set(classStudents.value.map((item) => item.id)))
const availableStudents = computed(() => {
  const existing = new Set(rows.value.filter((item) => item.cycle_id === createForm.cycle_id).map((item) => item.student_id))
  return allStudents.value.filter((item) => !existing.has(item.id))
})

function openCase(row) {
  router.push(`/teacher/student-cases/${row.id}`)
}

function applyWorkFilter() {
  status.value = ''
  load()
}

function onStatusChange() {
  workFilter.value = 'all'
  load()
}

async function openCreate() {
  creating.value = true
  try {
    ;[cycles.value, classes.value, allStudents.value] = await Promise.all([
      listCaseCycles(),
      listClasses(),
      listUsers('student'),
    ])
    const activeCycle = cycles.value.find((item) => item.is_active) || cycles.value[0]
    const firstClass = availableClasses.value[0]
    // 默认学年优先跟随首选班级的学年，其次跟随活动周期，再回落到 2026-2027
    const defaultYear = firstClass?.school_year || activeCycle?.school_year || '2026-2027'
    const defaultCycle = cycles.value.find((c) => c.school_year === defaultYear)
    const defaultCycleId = defaultCycle ? defaultCycle.id : defaultYear
    Object.assign(createForm, {
      cycle_id: defaultCycleId,
      class_id: firstClass?.id || null,
      student_id: null,
      parent_evaluation: '',
      primary_needs: '',
      current_summary: '班主任手工建档，待完善学科方案',
    })
    if (firstClass) await loadClassStudents(firstClass.id)
    createVisible.value = true
  } finally {
    creating.value = false
  }
}

async function loadClassStudents(classId) {
  createForm.student_id = null
  classStudents.value = classId ? await listStudents(classId) : []
}

async function submitCreate() {
  if (!createForm.cycle_id || !createForm.class_id || !createForm.student_id) {
    ElMessage.warning('请选择学年、班级和学生')
    return
  }
  creating.value = true
  try {
    // 若选择的是尚未落库的学年（虚拟选项，值为 "2027-2028" 这类），先按班级学年范围自动创建周期
    let cycleId = createForm.cycle_id
    if (typeof cycleId === 'string' && cycleId.includes('-')) {
      const year = cycleId
      const startYear = Number.parseInt(year.split('-')[0], 10)
      const payload = {
        name: `${year}学年`,
        school_year: year,
        starts_on: `${startYear}-08-01`,
        ends_on: `${startYear + 1}-06-30`,
      }
      const createdCycle = await createCaseCycle(payload)
      // 刷新本地周期缓存，避免下次重复创建
      cycles.value.push(createdCycle)
      cycleId = createdCycle.id
    }
    if (!classStudentIds.value.has(createForm.student_id)) {
      await addStudents(createForm.class_id, [createForm.student_id])
    }
    const created = await createStudentCase({ ...createForm, cycle_id: cycleId, owner_teacher_id: auth.user.id })
    ElMessage.success('学生总案已创建')
    createVisible.value = false
    router.push(`/teacher/student-cases/${created.id}`)
  } finally {
    creating.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const params = status.value ? { status: status.value } : {}
    ;[rows.value, progress.value] = await Promise.all([listStudentCases(params), getCaseProgress()])
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.cases-page {
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

.overline {
  font-size: 11px;
  color: #7a8599;
  letter-spacing: 0.04em;
  display: block;
  margin-bottom: 6px;
}

.page-head h1 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.page-head p {
  margin: 0;
  font-size: 13px;
  color: var(--ink-muted);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px 12px;
  display: flex;
  flex-direction: column;
}

.total-card {
  background: #fbfcff;
  border-color: #dbe4ff;
}

.is-warn {
  background: #fffbf3;
  border-color: #fde6bf;
}

.kpi-label {
  font-size: 12px;
  color: var(--ink-muted);
}

.kpi-num {
  margin: 6px 0 2px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.kpi-num.is-danger {
  color: #c2410c;
}

.kpi-sub {
  font-size: 11px;
  color: #9aa6b8;
}

.list-container {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}

.list-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line-soft);
  background: #fbfcfe;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-left h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.count-tag {
  font-size: 11.5px;
  color: var(--ink-muted);
  background: #ffffff;
  border: 1px solid var(--line);
  padding: 2px 7px;
  border-radius: 6px;
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cases-table {
  cursor: pointer;
}

.student-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-avatar {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: #eef2ff;
  color: #2f5bff;
  border: 1px solid #dfe6ff;
  display: grid;
  place-items: center;
  font-weight: 600;
  font-size: 12.5px;
  flex-shrink: 0;
}

.student-info {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.student-info strong {
  font-size: 13.5px;
  color: var(--ink);
  font-weight: 600;
}

.student-info small {
  font-size: 11px;
  color: #9aa6b8;
}

.version-tag {
  font-size: 12px;
  color: #475569;
  font-family: monospace;
}

.create-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 1024px) {
  .kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .kpi-grid {
    grid-template-columns: 1fr 1fr;
  }
  .page-head, .list-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .filters {
    flex-wrap: wrap;
  }
}
</style>
