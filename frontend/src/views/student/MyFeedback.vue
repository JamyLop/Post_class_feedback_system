<template>
  <div class="page">
    <div class="page-header"><span class="page-title">课后反馈</span></div>
    <el-empty v-if="!reports.length" description="暂无已发布反馈" />
    <el-card v-for="report in reports" :key="report.id" shadow="never" style="margin-bottom: 16px">
      <template #header>
        {{ report.report_type === 'weekly' ? `周报 ${report.period_start} 至 ${report.period_end}` : `作业反馈 #${report.assignment_id}` }}
      </template>
      <div class="content">{{ report.final_content }}</div>
      <div class="date">发布时间：{{ formatDate(report.published_at) }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { listFeedback } from '../../api/feedback'

const auth = useAuthStore()
const reports = ref([])
const formatDate = (value) => value ? new Date(value).toLocaleString() : '-'

onMounted(async () => {
  if (auth.user?.id) reports.value = await listFeedback(auth.user.id)
})
</script>

<style scoped>
.content { white-space: pre-wrap; line-height: 1.8; color: #303133; }
.date { margin-top: 16px; color: #909399; font-size: 12px; }
</style>
