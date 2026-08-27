<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">班级管理</span>
      <el-button type="primary" @click="openDialog">新建班级</el-button>
    </div>
    <el-table :data="classes" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="班级名称" />
      <el-table-column prop="school_year" label="学年" width="150" />
      <el-table-column prop="grade" label="年级" />
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/teacher/classes/${row.id}/students`)">
            学生管理
          </el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑班级' : '新建班级'" width="460px">
      <el-form :model="form" label-position="top">
        <el-form-item label="学年">
          <el-select v-model="form.school_year" placeholder="选择学年" style="width: 100%"><el-option v-for="year in schoolYears" :key="year" :label="`${year}学年`" :value="year" /></el-select>
        </el-form-item>
        <el-form-item label="班级名称">
          <el-input v-model="form.name" placeholder="如：高三1班" />
        </el-form-item>
        <el-form-item label="年级">
          <el-select v-model="form.grade" placeholder="选择年级" style="width: 100%"><el-option v-for="grade in grades" :key="grade" :label="grade" :value="grade" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createClass, deleteClass, listClasses, updateClass } from '../../api/classes'

const classes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const form = reactive({ name: '', grade: '高三', school_year: '2026-2027' })
const grades = ['高一', '高二', '高三', '初一', '初二', '初三']
const schoolYears = ['2025-2026', '2026-2027', '2027-2028']

async function load() {
  loading.value = true
  try {
    classes.value = await listClasses()
  } finally {
    loading.value = false
  }
}

function openDialog() {
  editingId.value = null
  form.name = ''
  form.grade = '高三'
  form.school_year = '2026-2027'
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, grade: row.grade, school_year: row.school_year || '未设置' })
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name || !form.grade || !form.school_year) {
    ElMessage.warning('请填写学年、班级名称和年级')
    return
  }
  if (editingId.value) await updateClass(editingId.value, { ...form })
  else await createClass({ ...form })
  ElMessage.success(editingId.value ? '班级信息已更新' : '班级已创建')
  dialogVisible.value = false
  load()
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除班级「${row.name}」？仅未关联档案、作业或反馈数据的班级可以删除。`, '删除班级', { type: 'warning', confirmButtonText: '确认删除' })
  } catch { return }
  await deleteClass(row.id)
  ElMessage.success('班级已删除，学生账号不会被删除')
  load()
}

onMounted(load)
</script>
