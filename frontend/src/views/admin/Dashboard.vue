<template>
  <div v-loading="loading" class="page dashboard-page">
    <div class="page-header">
      <div>
        <span class="overline">校级 · 基础数据</span>
        <h1 class="page-title">系统概览</h1>
        <p class="header-desc">全校人员、班级与一生一案进展一览。</p>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>

    <!-- 5 卡一行：删除作业/提交 -->
    <div class="stats-grid stats-grid--5">
      <div v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <div class="stat-value">{{ card.value }}</div>
        <span class="stat-note">{{ card.note }}</span>
      </div>
    </div>

    <!-- 看板图 -->
    <div class="board-grid">
      <div class="board-card">
        <div class="board-title">
          <span>人员构成</span>
          <small>教师 / 学生 / 家长 / 管理</small>
        </div>
        <EChart :option="rolePieOption" height="260px" />
        <div class="board-foot">
          <span>总人数 {{ stats.user_count ?? '-' }}</span>
          <span class="muted">德育主任 {{ stats.deyu_director_count ?? 0 }} 人</span>
        </div>
      </div>

      <div class="board-card">
        <div class="board-title">
          <span>一生一案状态分布</span>
          <small>共 {{ progress.total ?? 0 }} 份档案</small>
        </div>
        <EChart :option="caseStatusOption" height="260px" />
        <div class="kpi-row">
          <span class="kpi kpi--warn">逾期任务 {{ progress.overdue_tasks ?? 0 }}</span>
          <span class="kpi kpi--info">久未复盘 {{ progress.long_unreviewed ?? 0 }}</span>
        </div>
      </div>
    </div>

    <div class="board-grid">
      <div class="board-card">
        <div class="board-title">
          <span>班级规模对比</span>
          <small>人数 · 按班级</small>
        </div>
        <EChart :option="classBarOption" height="280px" />
        <div v-if="!classStats.length" class="empty-tip">暂无班级数据</div>
      </div>

      <div class="board-card">
        <div class="board-title">
          <span>档案健康度</span>
          <small>执行与待复盘</small>
        </div>
        <EChart :option="healthOption" height="280px" />
        <div class="board-foot">
          <span>执行中 {{ progress.executing ?? 0 }}</span>
          <span>待复盘 {{ progress.pending_review ?? 0 }}</span>
          <span>已归档 {{ progress.archived ?? 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAdminStats } from '../../api/admin'
import EChart from '../../components/EChart.vue'
import { getCaseProgress } from '../../api/studentCases'
import { listClasses, listStudents } from '../../api/classes'

const stats = ref({})
const progress = ref({})
const classStats = ref([])
const loading = ref(false)

const cards = computed(() => [
  { label: '用户总数', value: stats.value.user_count ?? '-', note: '全部角色' },
  { label: '教师', value: stats.value.teacher_count ?? '-', note: '任课与班主任' },
  { label: '学生', value: stats.value.student_count ?? '-', note: '在校学生' },
  { label: '管理员', value: stats.value.admin_count ?? '-', note: '校级管理' },
  { label: '班级', value: stats.value.class_count ?? '-', note: '已开班级' },
])

const rolePieOption = computed(() => {
  const d = stats.value
  const data = [
    { value: d.teacher_count || 0, name: '班主任' },
    { value: d.subject_teacher_count || 0, name: '任课老师' },
    { value: d.student_count || 0, name: '学生' },
    { value: d.parent_count || 0, name: '家长' },
    { value: d.admin_count || 0, name: '校级管理' },
    { value: d.deyu_director_count || 0, name: '德育主任' },
    { value: d.consultant_count || 0, name: '咨询老师' },
  ].filter(i => i.value > 0)
  return {
    tooltip: { trigger: 'item' },
    color: ['#3b82f6', '#14b8a6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899'],
    series: [{
      type: 'pie',
      radius: ['52%', '78%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12 } },
      labelLine: { show: false },
      data: data.length ? data : [{ value: 1, name: '暂无数据' }],
    }],
  }
})

const STATUS_LABELS = {
  draft: '草稿',
  pending_confirmation: '待确认',
  revision_required: '需修订',
  executing: '执行中',
  pending_review: '待复盘',
  adjusted: '已调整',
  archived: '已归档',
}
const caseStatusOption = computed(() => {
  const p = progress.value
  const keys = ['draft', 'pending_confirmation', 'revision_required', 'executing', 'pending_review', 'adjusted', 'archived']
  const data = keys.map(k => ({ value: p[k] || 0, name: STATUS_LABELS[k] }))
  const hasData = data.some(d => d.value > 0)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 12, right: 12, top: 8, bottom: 24, containLabel: true },
    xAxis: { type: 'category', data: keys.map(k => STATUS_LABELS[k]), axisLabel: { interval: 0, rotate: 18, fontSize: 11 } },
    yAxis: { type: 'value', minInterval: 1 },
    color: ['#6366f1'],
    series: [{
      type: 'bar',
      barMaxWidth: 32,
      itemStyle: { borderRadius: [6, 6, 0, 0] },
      data: hasData ? data.map(d => d.value) : [0, 0, 0, 0, 0, 0, 0],
    }],
  }
})

const classBarOption = computed(() => {
  const list = classStats.value
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 12, right: 12, top: 8, bottom: list.length > 6 ? 60 : 24, containLabel: true },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: list.map(i => i.name), axisLabel: { width: 90, overflow: 'truncate' } },
    color: ['#0ea5e9'],
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      itemStyle: { borderRadius: [0, 6, 6, 0] },
      data: list.map(i => i.count),
    }],
  }
})

const healthOption = computed(() => {
  const p = progress.value
  const total = p.total || 0
  const executing = p.executing || 0
  const pending = (p.pending_review || 0) + (p.pending_confirmation || 0)
  const done = (p.archived || 0) + (p.adjusted || 0)
  const remain = Math.max(total - executing - pending - done, 0)
  const data = [
    { value: executing, name: '执行中' },
    { value: pending, name: '待处理' },
    { value: done, name: '已完成' },
    { value: remain, name: '其他' },
  ].filter(i => i.value > 0)
  return {
    tooltip: { trigger: 'item' },
    color: ['#10b981', '#f59e0b', '#6366f1', '#e5e7eb'],
    series: [{
      type: 'pie',
      radius: ['48%', '72%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: data.length ? data : [{ value: 1, name: '暂无档案' }],
    }],
  }
})

async function load() {
  loading.value = true
  try {
    const [s, prog] = await Promise.all([
      getAdminStats(),
      getCaseProgress().catch(() => ({})),
    ])
    stats.value = s || {}
    progress.value = prog || {}

    // 班级规模：并行拉取每班人数（班级不多，避免 N+1 过重）
    try {
      const classes = await listClasses()
      const arr = Array.isArray(classes) ? classes : []
      const counts = await Promise.all(arr.slice(0, 12).map(async c => {
        try {
          const students = await listStudents(c.id)
          return { name: c.name, count: Array.isArray(students) ? students.length : 0 }
        } catch {
          return { name: c.name, count: 0 }
        }
      }))
      // 按人数倒序
      classStats.value = counts.sort((a, b) => b.count - a.count)
    } catch {
      classStats.value = []
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.overline {
  font-size: 11px;
  color: #7a8599;
  letter-spacing: 0.04em;
  display: block;
  margin-bottom: 4px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
}

.header-desc {
  margin: 0;
  font-size: 13px;
  color: var(--ink-muted);
}

.stats-grid {
  display: grid;
  gap: 12px;
}
.stats-grid--5 {
  grid-template-columns: repeat(5, 1fr);
}

.stat-card {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 12px;
  color: var(--ink-muted);
}

.stat-value {
  margin: 4px 0 2px;
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.stat-note {
  font-size: 11px;
  color: #9aa6b8;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.board-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px 12px;
  display: flex;
  flex-direction: column;
}

.board-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}
.board-title small {
  font-weight: 400;
  font-size: 11px;
  color: #8a97ad;
}

.board-foot {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  font-size: 11px;
  color: #6b7280;
}
.board-foot .muted { color: #9aa6b8; }

.kpi-row {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.kpi {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #f3f4f6;
}
.kpi--warn { background: #fef3c7; color: #92400e; }
.kpi--info { background: #e0e7ff; color: #3730a3; }

.empty-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #9aa6b8;
  text-align: center;
}

@media (max-width: 1100px) {
  .stats-grid--5 { grid-template-columns: repeat(3, 1fr); }
  .board-grid { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  .stats-grid--5 { grid-template-columns: repeat(2, 1fr); }
}
</style>
