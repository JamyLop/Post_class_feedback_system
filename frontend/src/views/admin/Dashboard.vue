<template>
  <div v-loading="loading" class="page dashboard-page">
    <div class="page-header">
      <div>
        <span class="overline">校级 · 基础数据</span>
        <h1 class="page-title">系统概览</h1>
        <p class="header-desc">全校用户、班级与作业提交情况一览。</p>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>

    <div class="stats-grid">
      <div v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <div class="stat-value">{{ card.value }}</div>
        <span class="stat-note">{{ card.note }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAdminStats } from '../../api/admin'

const stats = ref({})
const loading = ref(false)

const cards = computed(() => [
  { label: '用户总数', value: stats.value.user_count ?? '-', note: '全部角色' },
  { label: '教师', value: stats.value.teacher_count ?? '-', note: '任课与班主任' },
  { label: '学生', value: stats.value.student_count ?? '-', note: '在校学生' },
  { label: '管理员', value: stats.value.admin_count ?? '-', note: '校级管理' },
  { label: '班级', value: stats.value.class_count ?? '-', note: '已开班级' },
  { label: '作业', value: stats.value.assignment_count ?? '-', note: '已发布' },
  { label: '提交', value: stats.value.submission_count ?? '-', note: '学生提交' },
])

async function load() {
  loading.value = true
  try {
    stats.value = await getAdminStats()
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
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
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

@media (max-width: 1024px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .stats-grid { grid-template-columns: 1fr; }
}
</style>
