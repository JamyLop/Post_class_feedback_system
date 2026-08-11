<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <span class="page-title">提交结果</span>
      <el-button @click="$router.push('/student/assignments')">返回作业列表</el-button>
    </div>
    <el-card v-if="submission">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="提交ID">{{ submission.id }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ { text: '文本', image: '图片', pdf: 'PDF' }[submission.content_type] }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusMap[submission.status] || 'info'">{{ statusLabel(submission.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ submission.submitted_at }}</el-descriptions-item>
        <el-descriptions-item label="文件" :span="2">
          <el-link v-if="submission.content_url" :href="'/api/storage/files/' + submission.content_url" target="_blank" type="primary">查看提交文件</el-link>
          <span v-else>—</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getSubmission } from '../../api/submissions'

const route = useRoute()
const submission = ref(null)
const loading = ref(false)
const statusMap = {
  submitted: 'info', processing: 'warning', ai_graded: 'success',
  teacher_reviewed: 'success', completed: 'success', failed: 'danger',
}
const statusLabel = (s) => ({
  submitted: '已提交', processing: '处理中', ai_graded: 'AI已批改',
  teacher_reviewed: '待复核', completed: '已完成', failed: '失败',
}[s] || s)

async function load() {
  loading.value = true
  try {
    submission.value = await getSubmission(route.params.id)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
