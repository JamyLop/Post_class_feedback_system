<template>
  <section class="page supervision-page">
    <header class="page-head">
      <div>
        <div class="scope-badges">
          <span class="badge-tag">校级决策与督导</span>
          <span class="badge-sub">高三学情驾驶舱</span>
        </div>
        <h1>高三督查驾驶舱</h1>
        <p>重点关注方案待确认、逾期任务、长期未督查和待复盘学生，为年级管理提供数据支撑。</p>
      </div>
    </header>

    <div class="metrics-grid">
      <div v-for="item in cards" :key="item.key" class="metric-card" :class="item.tone">
        <div class="metric-header">
          <span class="metric-dot"></span>
          <span class="metric-label">{{ item.label }}</span>
        </div>
        <div class="metric-num">{{ progress[item.key] || 0 }}</div>
      </div>
    </div>

    <div class="table-container">
      <div class="table-head">
        <div>
          <h2>高三学生总案监控表</h2>
          <span class="count-tag">实时数据</span>
        </div>
        <el-button :loading="loading" @click="load">刷新数据</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" empty-text="尚无高三试点数据" class="supervision-table">
        <el-table-column prop="student_name" label="学生姓名" min-width="140" />
        <el-table-column prop="class_name" label="所属班级" min-width="140" />
        <el-table-column prop="admission_target" label="升学目标" min-width="260" show-overflow-tooltip />
        <el-table-column label="当前状态" width="130">
          <template #default="{ row }">
            <span class="badge-status" :class="`is-${row.status}`">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="90">
          <template #default="{ row }">
            <span class="version-tag">V{{ row.version }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'

const loading = ref(false), rows = ref([]), progress = ref({})

const cards = computed(() => [
  { key: 'total', label: '高三总案数', tone: 'tone-primary' },
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

async function load() {
  loading.value = true
  try {
    ;[progress.value, rows.value] = await Promise.all([getCaseProgress(), listStudentCases()])
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
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}

.metric-card {
  padding: 16px 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
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

.metric-card.tone-red .metric-num {
  color: #dc2626;
}

.table-container {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
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

@media (max-width: 1100px) {
  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 600px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
