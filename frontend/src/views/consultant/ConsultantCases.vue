<template>
  <section class="page cases-page">
    <header class="page-head">
      <div class="head-info">
        <span class="overline">咨询辅导</span>
        <h1>关联学生档案</h1>
        <p>查看你负责咨询辅导的学生档案；可新建学生并为其新建档案，辅导建议请在档案详情页的督查复盘中提交。</p>
      </div>
      <div class="head-actions">
        <el-button @click="openCreateStudent">新建学生</el-button>
        <el-button type="primary" @click="openCreateCase">新建档案</el-button>
      </div>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card total-card">
        <span class="kpi-label">关联学生档案</span>
        <div class="kpi-num">{{ rows.length }}</div>
        <span class="kpi-sub">已建档</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">执行中</span>
        <div class="kpi-num">{{ progress.executing || 0 }}</div>
        <span class="kpi-sub">进行中</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">待复盘</span>
        <div class="kpi-num">{{ progress.pending_review || 0 }}</div>
        <span class="kpi-sub">需要关注</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">已归档</span>
        <div class="kpi-num">{{ progress.archived || 0 }}</div>
        <span class="kpi-sub">已完成</span>
      </div>
    </div>

    <div class="list-container">
      <div class="list-toolbar">
        <div class="toolbar-left">
          <h2>学生档案列表</h2>
          <span class="count-tag">共 {{ filteredRows.length }} 人</span>
        </div>
        <div class="filters">
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索学生姓名"
            :prefix-icon="Search"
            style="width: 200px"
          />
          <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredRows"
        empty-text="暂无关联学生档案，可新建学生并建档，或联系管理员分配咨询关系"
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
        <el-table-column label="所属班级" min-width="140">
          <template #default="{ row }">
            <span>{{ row.class_name || '未分班' }}</span>
          </template>
        </el-table-column>
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
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openCase(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建学生：只录档案信息、不选班级，账号自动生成并关联自己；班主任后续从已有学生中挑入班级 -->
    <el-dialog v-model="studentVisible" title="新建学生" width="560px" destroy-on-close>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="仅需录入学生信息，无需选择班级，账号自动生成并关联你为咨询老师；班主任后续在班级名册“选择已有学生”将其加入班级"
        style="margin-bottom: 14px"
      />
      <el-form :model="studentForm" label-width="92px" @submit.prevent>
        <el-form-item label="姓名" required>
          <el-input v-model="studentForm.name" placeholder="请输入学生姓名" maxlength="64" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="studentForm.gender" clearable placeholder="请选择" style="width: 100%">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="民族">
          <el-input v-model="studentForm.ethnicity" placeholder="例如：汉族" maxlength="32" />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="studentForm.grade" placeholder="例如：高三" maxlength="32" />
        </el-form-item>
        <el-form-item label="生源地学校">
          <el-input v-model="studentForm.source_school" placeholder="填写学生原就读学校" maxlength="128" />
        </el-form-item>
        <el-form-item label="宿舍号">
          <el-input v-model="studentForm.dorm_number" placeholder="例如：3号楼205" maxlength="32" />
        </el-form-item>
        <el-form-item label="了解渠道">
          <el-input v-model="studentForm.channel" placeholder="选填，例如：转介绍 / 线上咨询" maxlength="64" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="studentVisible = false">取消</el-button>
        <el-button type="primary" :loading="studentCreating" @click="submitStudent">新建学生</el-button>
      </template>
    </el-dialog>

    <!-- 新建档案：只选自己关联的学生，班级自动带出 -->
    <el-dialog v-model="caseVisible" title="新建学生档案" width="600px" destroy-on-close>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只需选择你关联的学生，所属班级自动带出；尚未加入班级的学生也可以直接建档，入班后档案自动挂到班级名下"
        style="margin-bottom: 14px"
      />
      <el-form label-position="top">
        <el-form-item label="学年">
          <el-select v-model="caseForm.cycle_id" placeholder="选择学年" filterable style="width:100%">
            <el-option v-for="item in cycleOptions" :key="item.id" :label="cycleLabel(item)" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生">
          <el-select v-model="caseForm.student_id" filterable placeholder="选择尚未建档的学生" style="width:100%" @change="onCaseStudentChange">
            <el-option
              v-for="item in availableCaseStudents"
              :key="`${item.class_id ?? 'none'}-${item.id}`"
              :label="item.class_id ? `${item.name}（${item.class_name}·${item.username}）` : `${item.name}（未分班·${item.username}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="selectedCaseClass" label="所属班级">
          <el-tag type="info">{{ selectedCaseClass }}</el-tag>
        </el-form-item>
        <el-form-item label="家长评价">
          <el-input
            v-model="caseForm.parent_evaluation"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 8 }"
            placeholder="记录家长对学生的评价、关注点或家校协同建议"
          />
        </el-form-item>
        <el-form-item label="主要需求">
          <el-input
            v-model="caseForm.primary_needs"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="例如：学生主要需求、期望支持方向或家校配合事项"
          />
        </el-form-item>
        <el-form-item label="当前状态说明">
          <el-input
            v-model="caseForm.current_summary"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="例如：咨询老师建档，待完善教学方案"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="caseVisible = false">取消</el-button>
        <el-button type="primary" :loading="caseCreating" @click="submitCase">创建并进入档案</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { getCaseProgress, listStudentCases, listCaseCycles, createCaseCycle, createStudentCase } from '../../api/studentCases'
import { listClasses, listStudents } from '../../api/classes'
import { createQuickStudent, listUsers } from '../../api/users'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const rows = ref([])
const progress = ref({})
const loading = ref(false)
const keyword = ref('')
const classes = ref([])
const cycles = ref([])

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
  const query = keyword.value.trim().toLowerCase()
  if (!query) return rows.value
  return rows.value.filter((row) =>
    `${row.student_name || ''}${row.class_name || ''}`.toLowerCase().includes(query),
  )
})

// 新建学生表单（免班级：只录档案信息）
const studentVisible = ref(false)
const studentCreating = ref(false)
const studentForm = reactive({
  name: '', gender: '', ethnicity: '', grade: '',
  source_school: '', dorm_number: '', channel: '',
})

// 新建档案表单（只选学生，班级自动带出）
const caseVisible = ref(false)
const caseCreating = ref(false)
const caseForm = reactive({
  cycle_id: null, class_id: null, student_id: null,
  parent_evaluation: '', primary_needs: '', current_summary: '咨询老师建档，待完善教学方案',
})
// 自己关联且已入班的学生（合并所有关联班级名册，附带班级信息）
const allCaseStudents = ref([])
const availableCaseStudents = computed(() => {
  const existing = new Set(rows.value.filter((item) => item.cycle_id === caseForm.cycle_id).map((item) => item.student_id))
  return allCaseStudents.value.filter((item) => !existing.has(item.id))
})
const selectedCaseClass = computed(() => {
  const hit = allCaseStudents.value.find((item) => item.id === caseForm.student_id)
  if (!hit) return ''
  return hit.class_id ? hit.class_name : '未分班（入班后自动挂靠）'
})
function onCaseStudentChange(studentId) {
  const hit = allCaseStudents.value.find((item) => item.id === studentId)
  caseForm.class_id = hit ? hit.class_id : null
}

function openCase(row) {
  if (!row?.id) return
  router.push(`/consultant/cases/${row.id}`)
}

async function load() {
  loading.value = true
  try {
    const [list, prog] = await Promise.all([
      listStudentCases(),
      getCaseProgress().catch(() => ({})),
    ])
    rows.value = Array.isArray(list) ? list : []
    progress.value = prog || {}
  } finally {
    loading.value = false
  }
}

async function openCreateStudent() {
  Object.assign(studentForm, {
    name: '', gender: '', ethnicity: '', grade: '',
    source_school: '', dorm_number: '', channel: '',
  })
  studentVisible.value = true
}

async function submitStudent() {
  if (!studentForm.name.trim()) return ElMessage.warning('请填写学生姓名')
  studentCreating.value = true
  try {
    await createQuickStudent({
      name: studentForm.name.trim(),
      gender: studentForm.gender || '',
      ethnicity: studentForm.ethnicity?.trim() || '',
      grade: studentForm.grade?.trim() || '',
      source_school: studentForm.source_school?.trim() || '',
      dorm_number: studentForm.dorm_number?.trim() || '',
      channel: studentForm.channel?.trim() || '',
    })
    ElMessage.success('新建学生成功，账号已自动生成；班主任可在班级名册“选择已有学生”将其加入班级')
    studentVisible.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    studentCreating.value = false
  }
}

async function openCreateCase() {
  caseCreating.value = true
  try {
    // 每次打开都刷新班级与学年，避免班主任刚加入的学生因缓存不显示
    classes.value = await listClasses()
    cycles.value = await listCaseCycles()
    if (!classes.value.length) {
      ElMessage.warning('暂无关联班级，请先新建学生并联系班主任将其加入班级，或联系管理员分配咨询关系')
      return
    }
    const activeCycle = cycles.value.find((item) => item.is_active) || cycles.value[0]
    const defaultYear = activeCycle?.school_year || '2026-2027'
    const defaultCycle = cycles.value.find((c) => c.school_year === defaultYear)
    Object.assign(caseForm, {
      cycle_id: defaultCycle ? defaultCycle.id : defaultYear,
      class_id: null,
      student_id: null,
      parent_evaluation: '',
      primary_needs: '',
      current_summary: '咨询老师建档，待完善教学方案',
    })
    // 合并所有关联班级的名册，学生选项自带班级，选中后自动带出班级；
    // 仅保留自己关联的学生（同班其他咨询的学生不出现）
    const [rosters, linkedStudents] = await Promise.all([
      Promise.all(classes.value.map((cls) => listStudents(cls.id).catch(() => []))),
      listUsers('student', '').catch(() => []),
    ])
    const linkedIds = new Set((linkedStudents || []).map((item) => item.id))
    const merged = []
    const inRoster = new Set()
    classes.value.forEach((cls, idx) => {
      for (const stu of rosters[idx] || []) {
        if (!linkedIds.has(stu.id)) continue
        inRoster.add(stu.id)
        merged.push({ ...stu, class_id: cls.id, class_name: cls.name })
      }
    })
    // 尚未加入任何班级的关联学生也可直接建档（未分班），入班后自动挂靠
    for (const stu of linkedStudents || []) {
      if (!inRoster.has(stu.id)) {
        merged.push({ ...stu, class_id: null, class_name: '' })
      }
    }
    allCaseStudents.value = merged
    if (!merged.length) {
      ElMessage.warning('没有可建档的学生：刚新建的学生须先由班主任加入班级后才会出现在这里')
      return
    }
    caseVisible.value = true
  } finally {
    caseCreating.value = false
  }
}

async function submitCase() {
  if (!caseForm.cycle_id || !caseForm.student_id) {
    ElMessage.warning('请选择学年和学生')
    return
  }
  caseCreating.value = true
  try {
    let cycleId = caseForm.cycle_id
    if (typeof cycleId === 'string' && cycleId.includes('-')) {
      const year = cycleId
      const startYear = Number.parseInt(year.split('-')[0], 10)
      const selectedClass = classes.value.find((item) => item.id === caseForm.class_id)
      const createdCycle = await createCaseCycle({
        name: `${year}学年`,
        school_year: year,
        starts_on: selectedClass?.school_year_starts_on || `${startYear}-08-01`,
        ends_on: `${startYear + 1}-06-30`,
      })
      cycles.value.push(createdCycle)
      cycleId = createdCycle.id
    }
    const selectedClass = classes.value.find((item) => item.id === caseForm.class_id)
    const ownerTeacherId = selectedClass?.teacher_id || auth.user.id
    const created = await createStudentCase({
      cycle_id: cycleId,
      class_id: caseForm.class_id,
      student_id: caseForm.student_id,
      owner_teacher_id: ownerTeacherId,
      parent_evaluation: caseForm.parent_evaluation,
      primary_needs: caseForm.primary_needs,
      current_summary: caseForm.current_summary,
    })
    ElMessage.success('学生档案已创建')
    caseVisible.value = false
    load()
    router.push(`/consultant/cases/${created.id}`)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    caseCreating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.cases-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.head-actions { display: flex; gap: 10px; flex-shrink: 0; }
.overline { font-size: 11px; color: #7a8599; letter-spacing: 0.04em; display: block; margin-bottom: 6px; }
.page-head h1 { margin: 0 0 4px; font-size: var(--font-size-page-title); font-weight: var(--font-weight-heading); color: var(--ink); letter-spacing: normal; }
.page-head p { margin: 0; font-size: 13px; color: var(--ink-muted); max-width: 640px; line-height: 1.6; }
.create-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi-card { background: #fff; border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px 12px; display: flex; flex-direction: column; }
.total-card { background: #faf5ff; border-color: #e9d5ff; }
.kpi-label { font-size: 12px; color: var(--ink-muted); }
.kpi-num { margin: 6px 0 2px; font-size: 24px; font-weight: var(--font-weight-heading); color: var(--ink); line-height: 1.1; font-variant-numeric: tabular-nums; }
.kpi-sub { font-size: 11px; color: #9aa6b8; }
.list-container { background: #fff; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.list-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 12px 16px; border-bottom: 1px solid var(--line-soft); background: #fdfaff; }
.toolbar-left { display: flex; align-items: center; gap: 10px; }
.toolbar-left h2 { margin: 0; font-size: 15px; font-weight: 600; color: var(--ink); }
.count-tag { font-size: 11.5px; color: var(--ink-muted); background: #fff; border: 1px solid var(--line); padding: 2px 7px; border-radius: 6px; }
.filters { display: flex; align-items: center; gap: 10px; }
.cases-table { cursor: pointer; }
.student-cell { display: flex; align-items: center; gap: 10px; }
.student-avatar {
  width: 30px; height: 30px; border-radius: 999px;
  background: #ede9fe; color: #6d28d9; border: 1px solid #ddd6fe;
  display: grid; place-items: center; font-weight: 600; font-size: 12.5px; flex-shrink: 0;
}
.student-info { display: flex; flex-direction: column; line-height: 1.3; }
.student-info strong { font-size: 13.5px; color: var(--ink); font-weight: 600; }
.student-info small { font-size: 11px; color: #9aa6b8; }
.version-tag { font-size: 12px; color: #475569; font-family: monospace; }
.badge-status { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #f1f5f9; border: 1px solid #e2e8f0; }
.badge-status.is-executing { background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
.badge-status.is-pending_review { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
.badge-status.is-pending_confirmation { background: #fffbeb; border-color: #fde68a; color: #92400e; }
.badge-status.is-revision_required { background: #fef2f2; border-color: #fecaca; color: #991b1b; }
@media (max-width: 1024px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .create-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) {
  .page-head, .list-toolbar { flex-direction: column; align-items: stretch; }
  .filters { flex-wrap: wrap; }
}
</style>
