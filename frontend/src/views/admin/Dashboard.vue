<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <span class="page-title">系统概览</span>
    </div>
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :span="6">
        <el-card class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAdminStats } from '../../api/admin'

const stats = ref({})
const loading = ref(false)

const cards = computed(() => [
  { label: '用户总数', value: stats.value.user_count ?? '-' },
  { label: '教师', value: stats.value.teacher_count ?? '-' },
  { label: '学生', value: stats.value.student_count ?? '-' },
  { label: '管理员', value: stats.value.admin_count ?? '-' },
  { label: '班级数', value: stats.value.class_count ?? '-' },
  { label: '作业数', value: stats.value.assignment_count ?? '-' },
  { label: '提交数', value: stats.value.submission_count ?? '-' },
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
.stat-card {
  margin-bottom: 16px;
}
.stat-label {
  color: #999;
  font-size: 13px;
}
.stat-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 600;
}
</style>
