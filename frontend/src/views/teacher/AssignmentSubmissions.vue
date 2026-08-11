<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">提交记录</span>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    <el-table :data="submissions" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="student_id" label="学生ID" width="100" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ { text: '文本', image: '图片', pdf: 'PDF' }[row.content_type] || row.content_type }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status] || 'info'">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="submitted_at" label="提交时间" />
      <el-table-column label="文件" width="100">
        <template #default="{ row }">
          <el-link v-if="row.content_url" :href="'/api/storage/files/' + row.content_url" target="_blank" type="primary">查看</el-link>
          <span v-else>—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { listSubmissions } from '../../api/submissions'

const route = useRoute()
const submissions = ref([])
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
    submissions.value = await listSubmissions(route.params.id)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
