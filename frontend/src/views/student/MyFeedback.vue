<template>
  <div class="page student-feedback-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">教师课后反馈与学情评语</h1>
        <p class="header-desc">查阅任课教师与班主任发布的作业针对性诊断指导与周度学情总结。</p>
      </div>
    </div>

    <el-empty v-if="!reports.length" description="暂无已发布的教师反馈评语" :image-size="80" />

    <div v-else class="reports-list">
      <el-card v-for="report in reports" :key="report.id" shadow="never" class="feedback-card">
        <template #header>
          <div class="card-head">
            <div class="head-left">
              <span class="report-badge" :class="{ 'is-weekly': report.report_type === 'weekly' }">
                {{ report.report_type === 'weekly' ? '周度学情' : '作业反馈' }}
              </span>
              <strong class="report-title">
                {{ report.report_type === 'weekly' ? `学情周报 (${report.period_start} 至 ${report.period_end})` : `作业诊断报告 #${report.assignment_id}` }}
              </strong>
            </div>
            <span class="pub-time">发布时间：{{ formatDate(report.published_at) }}</span>
          </div>
        </template>
        <div class="content">{{ report.final_content }}</div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { listFeedback } from '../../api/feedback'

const auth = useAuthStore()
const reports = ref([])
const formatDate = (value) => (value ? new Date(value).toLocaleString() : '-')

onMounted(async () => {
  if (auth.user?.id) reports.value = await listFeedback(auth.user.id)
})
</script>

<style scoped>
.student-feedback-page {
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

.feedback-card {
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

.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-badge {
  font-size: 11px;
  font-weight: 600;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 7px;
  border-radius: 6px;
}

.report-badge.is-weekly {
  color: #059669;
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.report-title {
  font-size: 14px;
  color: var(--ink);
}

.pub-time {
  color: #94a3b8;
  font-size: 12px;
  font-family: monospace;
}

.content {
  white-space: pre-wrap;
  line-height: 1.7;
  color: #334155;
  font-size: 13.5px;
}
</style>
