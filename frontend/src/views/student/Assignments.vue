<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">我的作业</span>
    </div>
    <el-table :data="assignments" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="subject" label="科目" width="100" />
      <el-table-column label="题目数" width="90">
        <template #default="{ row }">{{ row.questions?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="due_at" label="截止时间" width="200" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/student/assignments/${row.id}`)">去做</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listAssignments } from '../../api/assignments'

const assignments = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    assignments.value = await listAssignments()
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
