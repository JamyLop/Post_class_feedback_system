<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">学生管理</span>
      <el-button type="primary" @click="dialogVisible = true">添加学生</el-button>
    </div>
    <el-table :data="students" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="name" label="姓名" />
    </el-table>

    <el-dialog v-model="dialogVisible" title="添加学生" width="520px">
      <el-input v-model="keyword" placeholder="搜索用户名/姓名" clearable style="margin-bottom: 12px" @input="onSearch" />
      <el-table
        :data="candidates"
        height="320"
        @selection-change="(rows) => (selected = rows)"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="name" label="姓名" />
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selected.length" @click="onAdd">添加选中学生</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { addStudents, listStudents, listUsers } from '../../api/classes'

const route = useRoute()
const classId = route.params.id
const students = ref([])
const candidates = ref([])
const keyword = ref('')
const selected = ref([])
const loading = ref(false)
const dialogVisible = ref(false)

async function load() {
  loading.value = true
  try {
    students.value = await listStudents(classId)
  } finally {
    loading.value = false
  }
}

async function onSearch() {
  candidates.value = await listUsers('student', keyword.value)
}

async function onAdd() {
  await addStudents(classId, selected.value.map((s) => s.id))
  ElMessage.success('添加成功')
  dialogVisible.value = false
  load()
}

onMounted(async () => {
  await load()
  candidates.value = await listUsers('student')
})
</script>
