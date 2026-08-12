<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">作业管理</span>
      <el-button type="primary" @click="$router.push('/teacher/assignments/new')">新建作业</el-button>
    </div>
    <el-table :data="assignments" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="subject" label="科目" width="100" />
      <el-table-column prop="class_id" label="班级ID" width="90" />
      <el-table-column label="题目数" width="90">
        <template #default="{ row }">{{ row.questions?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status] || 'info'">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}`)">详情</el-button>
          <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}/submissions`)">提交</el-button>
          <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}/analysis`)">分析</el-button>
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
const statusMap = { draft: 'info', published: 'success', closed: 'warning', archived: 'info' }

function statusLabel(s) {
  return { draft: '草稿', published: '已发布', closed: '已关闭', archived: '已归档' }[s] || s
}

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
