<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">班级管理</span>
      <el-button type="primary" @click="openDialog">新建班级</el-button>
    </div>
    <el-table :data="classes" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="班级名称" />
      <el-table-column prop="grade" label="年级" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/teacher/classes/${row.id}/students`)">
            学生管理
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建班级" width="420px">
      <el-form :model="form" label-width="60px">
        <el-form-item label="班级名称">
          <el-input v-model="form.name" placeholder="如：初二3班" />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="form.grade" placeholder="如：初二" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createClass, listClasses } from '../../api/classes'

const classes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ name: '', grade: '' })

async function load() {
  loading.value = true
  try {
    classes.value = await listClasses()
  } finally {
    loading.value = false
  }
}

function openDialog() {
  form.name = ''
  form.grade = ''
  dialogVisible.value = true
}

async function onCreate() {
  if (!form.name || !form.grade) {
    ElMessage.warning('请填写班级名称和年级')
    return
  }
  await createClass({ ...form })
  ElMessage.success('创建成功')
  dialogVisible.value = false
  load()
}

onMounted(load)
</script>
