<template>
  <section class="page cases-page">
    <header class="page-head">
      <div>
        <div class="scope-line">
          <span>德育审查</span>
          <span>班主任方案 · 待审与已审</span>
        </div>
        <h1>德育主任审查台</h1>
        <p>查看全部学生总案，重点审查待复盘方案，提交德育督导与行为改进建议。</p>
      </div>
    </header>

    <div class="kpi-grid">
      <button class="kpi-card total" :class="{ 'is-active': activeKpi === 'total' }" type="button" @click="handleKpiClick('total')">
        <span class="kpi-label">档案总数</span>
        <div class="kpi-value">{{ progress.total || 0 }}</div>
        <span class="kpi-sub">德育覆盖范围</span>
      </button>
      <button class="kpi-card" :class="{ 'is-active': activeKpi === 'pending' }" type="button" @click="handleKpiClick('pending')">
        <div class="kpi-head">
          <span class="kpi-dot is-warning"></span>
          <span class="kpi-label">待我审查</span>
        </div>
        <div class="kpi-value">{{ progress.pending_confirmation || 0 }}</div>
        <span class="kpi-sub">班主任已提交</span>
      </button>
      <button class="kpi-card" :class="{ 'is-active': activeKpi === 'executing' }" type="button" @click="handleKpiClick('executing')">
        <div class="kpi-head">
          <span class="kpi-dot is-success"></span>
          <span class="kpi-label">正在执行</span>
        </div>
        <div class="kpi-value">{{ progress.executing || 0 }}</div>
        <span class="kpi-sub">平稳推进中</span>
      </button>
      <button class="kpi-card" :class="{ 'is-active': activeKpi === 'adjusted' }" type="button" @click="handleKpiClick('adjusted')">
        <div class="kpi-head">
          <span class="kpi-dot is-brand"></span>
          <span class="kpi-label">已调整总案</span>
        </div>
        <div class="kpi-value">{{ progress.adjusted || 0 }}</div>
        <span class="kpi-sub">完成方案优化</span>
      </button>
      <button class="kpi-card" :class="{ 'is-active': activeKpi === 'overdue' }" type="button" @click="handleKpiClick('overdue')">
        <div class="kpi-head">
          <span class="kpi-dot is-danger"></span>
          <span class="kpi-label">逾期微任务</span>
        </div>
        <div class="kpi-value">{{ progress.overdue_tasks || 0 }}</div>
        <span class="kpi-sub">待跟进提醒</span>
      </button>
    </div>

    <section class="list-surface">
      <div class="list-toolbar">
        <div>
          <h2>学生档案</h2>
          <span>共 {{ filteredRows.length }} 人</span>
        </div>
        <div class="filters">
          <el-select v-model="workFilter" style="width: 130px">
            <el-option label="全部档案" value="all" />
            <el-option label="待我审查" value="need_review" />
            <el-option label="已审/已调整" value="reviewed" />
          </el-select>
          <el-input v-model="keyword" clearable placeholder="搜索学生或班级" :prefix-icon="Search" style="width: 180px" />
          <el-select v-model="status" clearable placeholder="全部状态" style="width: 130px" @change="load">
            <el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="filteredRows" empty-text="暂无符合条件的学生总案" class="cases-table" @row-click="openCase">
        <el-table-column label="学生" min-width="150">
          <template #default="{ row }">
            <div class="student-cell">
              <span class="student-avatar">{{ row.student_name?.slice(0, 1) }}</span>
              <div>
                <strong>{{ row.student_name }}</strong>
                <small>档案 #{{ row.id }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column prop="admission_target" label="升学目标" min-width="240" show-overflow-tooltip />
        <el-table-column label="方案状态" width="120">
          <template #default="{ row }">
            <span class="badge-status" :class="`is-${row.status}`">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="版本" width="90">
          <template #default="{ row }">V{{ row.version }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openCase(row)">审查 / 查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'

const router = useRouter()
const rows = ref([])
const loading = ref(false)
const status = ref('')
const keyword = ref('')
const workFilter = ref('all')
const progress = ref({ total: 0, pending_confirmation: 0, revision_required: 0, executing: 0, adjusted: 0, overdue_tasks: 0 })

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

const activeKpi = ref('total')
const filteredRows = computed(() => {
  let result = rows.value
  if (workFilter.value === 'need_review') result = result.filter((row) => row.status === 'pending_confirmation')
  if (workFilter.value === 'reviewed') result = result.filter((row) => ['revision_required', 'executing', 'adjusted', 'archived'].includes(row.status))
  const query = keyword.value.trim().toLowerCase()
  if (query) result = result.filter((row) => `${row.student_name || ''}${row.class_name || ''}`.toLowerCase().includes(query))
  return result
})

function handleKpiClick(type) {
  activeKpi.value = type
  if (type === 'total') { status.value = ''; workFilter.value = 'all' }
  else if (type === 'pending') { status.value = 'pending_confirmation'; workFilter.value = 'need_review' }
  else if (type === 'executing') { status.value = 'executing'; workFilter.value = 'all' }
  else if (type === 'adjusted') { status.value = 'adjusted'; workFilter.value = 'all' }
  else if (type === 'overdue') { status.value = ''; workFilter.value = 'all' }
  if (type === 'overdue') {
    // 逾期微任务暂以后端统计为准，筛出执行中/待复盘等可能逾期的档案
    keyword.value = ''
  }
  load()
}

function openCase(row) {
  router.push(`/deyu/cases/${row.id}`)
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

.scope-line {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.scope-line span {
  font-size: 11px;
  font-weight: 600;
  color: #059669;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
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
  letter-spacing: -0.02em;
  font-weight: 700;
  color: var(--ink);
}

.page-head p {
  margin: 0;
  color: #64748b;
  font-size: 13.5px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: 1.2fr repeat(4, 1fr);
  gap: 14px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  padding: 16px 18px;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  text-align: left;
  width: 100%;
  font: inherit;
  transition: border-color .18s, box-shadow .18s, transform .12s;
}
.kpi-card:hover { border-color: #cbd5e1; box-shadow: 0 4px 12px rgba(15,23,42,.08); transform: translateY(-1px); }
.kpi-card.is-active { border-color: var(--brand, #2f5bff); box-shadow: 0 0 0 2px color-mix(in oklch, var(--brand, #2f5bff) 18%, transparent), 0 4px 12px rgba(15,23,42,.08); }
.kpi-card.total.is-active { border-color: #0f172a; box-shadow: 0 0 0 2px rgba(15,23,42,.2); }
.kpi-card:focus-visible { outline: 2px solid var(--brand, #2f5bff); outline-offset: 2px; }

.kpi-card.total {
  background: var(--ink);
  border-color: var(--ink);
  color: #ffffff;
}

.kpi-card.total .kpi-label {
  color: #94a3b8;
}

.kpi-card.total .kpi-value {
  color: #ffffff;
}

.kpi-card.total .kpi-sub {
  color: #64748b;
}

.kpi-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.kpi-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.kpi-dot.is-warning { background: #d97706; }
.kpi-dot.is-success { background: #059669; }
.kpi-dot.is-brand { background: #2f5bff; }
.kpi-dot.is-danger { background: #dc2626; }

.kpi-label {
  font-size: 12.5px;
  font-weight: 500;
  color: #64748b;
}

.kpi-value {
  margin: 8px 0 4px;
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.kpi-sub {
  font-size: 11.5px;
  color: #94a3b8;
}

.list-surface {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
}

.list-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.list-toolbar h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.list-toolbar span {
  color: #64748b;
  font-size: 11.5px;
  margin-left: 8px;
}

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.student-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: #059669;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 6px;
  font-weight: 600;
  font-size: 12px;
}

.student-cell strong {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink);
}

.student-cell small {
  display: block;
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 1024px) {
  .kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 680px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }
}
</style>
