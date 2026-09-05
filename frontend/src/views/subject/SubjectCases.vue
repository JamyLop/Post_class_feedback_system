<template>
  <section class="page cases-page">
    <header class="page-head">
      <div class="head-info">
        <span class="overline">任课协同 · 只读</span>
        <h1>所带班级档案</h1>
        <p>仅展示你所带学科的班级档案与科目方案；修改意见请在档案详情页提交学科建议，由班主任采纳维护。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card total-card">
        <span class="kpi-label">所带班级档案</span>
        <div class="kpi-num">{{ rows.length }}</div>
        <span class="kpi-sub">已建档</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">所带班级</span>
        <div class="kpi-num">{{ classes.length }}</div>
        <span class="kpi-sub">{{ classes.map((c) => c.name).slice(0, 3).join('、') || '待分配' }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">执行中</span>
        <div class="kpi-num">{{ progress.executing || 0 }}</div>
        <span class="kpi-sub">进行中</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">待处理</span>
        <div class="kpi-num">{{ todoCount }}</div>
        <span class="kpi-sub">草稿 / 整改 / 复盘</span>
      </div>
    </div>

    <div class="list-container">
      <div class="list-toolbar">
        <div class="toolbar-left">
          <h2>学生档案列表</h2>
          <span class="count-tag">共 {{ filteredRows.length }} 人</span>
        </div>
        <div class="filters">
          <el-select v-model="classId" clearable placeholder="全部班级" style="width: 160px" @change="load">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索学生"
            :prefix-icon="Search"
            style="width: 200px"
          />
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredRows"
        empty-text="暂无所带班级的学生档案，请联系管理员分配任课关系"
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
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openCase(row)">查看方案并提建议</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { listClasses } from '../../api/classes'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'

const router = useRouter()
const rows = ref([])
const classes = ref([])
const progress = ref({})
const loading = ref(false)
const keyword = ref('')
const classId = ref(null)

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

const todoCount = computed(() =>
  rows.value.filter((r) => ['draft', 'revision_required', 'pending_review'].includes(r.status)).length,
)
const filteredRows = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return rows.value
  return rows.value.filter((row) =>
    `${row.student_name || ''}${row.class_name || ''}`.toLowerCase().includes(query),
  )
})

function openCase(row) {
  if (!row?.id) return
  router.push(`/subject/cases/${row.id}`)
}

async function load() {
  loading.value = true
  try {
    const params = classId.value ? { class_id: classId.value } : {}
    const [list, prog, cls] = await Promise.all([
      listStudentCases(params),
      getCaseProgress(params).catch(() => ({})),
      listClasses().catch(() => []),
    ])
    rows.value = Array.isArray(list) ? list : []
    progress.value = prog || {}
    classes.value = Array.isArray(cls) ? cls : []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.cases-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.overline { font-size: 11px; color: #7a8599; letter-spacing: 0.04em; display: block; margin-bottom: 6px; }
.page-head h1 { margin: 0 0 4px; font-size: 20px; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; }
.page-head p { margin: 0; font-size: 13px; color: var(--ink-muted); max-width: 640px; line-height: 1.6; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi-card { background: #fff; border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px 12px; display: flex; flex-direction: column; }
.total-card { background: #fbfcff; border-color: #dbe4ff; }
.kpi-label { font-size: 12px; color: var(--ink-muted); }
.kpi-num { margin: 6px 0 2px; font-size: 24px; font-weight: 700; color: var(--ink); line-height: 1.1; font-variant-numeric: tabular-nums; }
.kpi-sub { font-size: 11px; color: #9aa6b8; }
.list-container { background: #fff; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.list-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 12px 16px; border-bottom: 1px solid var(--line-soft); background: #fbfcfe; }
.toolbar-left { display: flex; align-items: center; gap: 10px; }
.toolbar-left h2 { margin: 0; font-size: 15px; font-weight: 600; color: var(--ink); }
.count-tag { font-size: 11.5px; color: var(--ink-muted); background: #fff; border: 1px solid var(--line); padding: 2px 7px; border-radius: 6px; }
.filters { display: flex; align-items: center; gap: 10px; }
.cases-table { cursor: pointer; }
.student-cell { display: flex; align-items: center; gap: 10px; }
.student-avatar {
  width: 30px; height: 30px; border-radius: 999px;
  background: #ccfbf1; color: #0f766e; border: 1px solid #99f6e4;
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
@media (max-width: 1024px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) {
  .page-head, .list-toolbar { flex-direction: column; align-items: stretch; }
  .filters { flex-wrap: wrap; }
}
</style>
