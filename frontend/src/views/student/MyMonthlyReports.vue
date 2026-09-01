<template>
  <section class="page student-monthly-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">月度学情诊断与总结</h1>
        <p class="header-desc">查阅班主任每月发布的综合学情报告、德育日常表现与后续攻坚方案。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新月度评价</el-button>
    </div>

    <el-empty v-if="!rows.length" description="班主任尚未发布本阶段月度评价" :image-size="80" />

    <div v-else class="reports-list">
      <el-card v-for="r in rows" :key="r.id" shadow="never" class="monthly-card">
        <template #header>
          <div class="card-head">
            <div class="head-title">
              <span class="month-chip">{{ r.month_label }}</span>
              <strong class="report-title">学情综合诊断月度评价</strong>
            </div>
            <span class="period-text">{{ r.period_start }} ~ {{ r.period_end }}</span>
          </div>
        </template>
        <div class="monthly-content">{{ r.final_content || r.ai_content }}</div>
        <div class="monthly-meta">
          <span>发布时间：{{ r.published_at ? new Date(r.published_at).toLocaleString() : '-' }}</span>
        </div>
      </el-card>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listMonthlyReports } from '../../api/monthlyReports'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const rows = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listMonthlyReports({ student_id: auth.user?.id })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.student-monthly-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.header-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.monthly-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.head-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.month-chip {
  font-size: 11px;
  font-weight: 700;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: monospace;
}

.report-title {
  font-size: 15px;
  color: var(--ink);
}

.period-text {
  font-size: 12px;
  color: #94a3b8;
  font-family: monospace;
}

.monthly-content {
  white-space: pre-wrap;
  line-height: 1.75;
  color: #334155;
  font-size: 14px;
}

.monthly-meta {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  font-size: 12px;
  color: #94a3b8;
}
</style>
