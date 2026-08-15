<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">用户管理</span>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>

    <el-radio-group v-model="role" style="margin-bottom: 12px" @change="load">
      <el-radio-button value="student">学生</el-radio-button>
      <el-radio-button value="teacher">教师</el-radio-button>
      <el-radio-button value="admin">管理员</el-radio-button>
    </el-radio-group>

    <el-input
      v-model="keyword"
      placeholder="搜索用户名/姓名"
      clearable
      style="width: 260px; margin-bottom: 12px"
      @input="load"
    />

    <el-table :data="users" v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">{{ roleLabel(row.role) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="row.role === 'student' || row.role === 'teacher'"
            link
            :type="row.status === 'active' ? 'warning' : 'success'"
            @click="toggleStatus(row)"
          >
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
          <el-button
            v-if="row.id !== auth.user?.id"
            link
            type="danger"
            @click="onDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新建用户'" width="440px">
      <el-form :model="form" label-width="70px">
        <el-form-item label="角色">
          <el-radio-group v-model="form.role" :disabled="editing">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">教师</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="editing" placeholder="用户名（3-64位）" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="姓名" />
        </el-form-item>
        <el-form-item :label="editing ? '新密码' : '密码'">
          <el-input v-model="form.password" type="password" show-password :placeholder="editing ? '留空则不修改' : '密码（至少6位）'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { listUsers, createUser, updateUser } from '../../api/users'
import { deleteUser as deleteUserApi } from '../../api/admin'

const auth = useAuthStore()
const users = ref([])
const role = ref('student')
const keyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(false)
const form = reactive({ role: 'student', username: '', name: '', password: '' })

function roleLabel(r) {
  return { admin: '管理员', teacher: '教师', student: '学生' }[r] || r
}

async function load() {
  loading.value = true
  try {
    users.value = await listUsers(role.value, keyword.value)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = false
  Object.assign(form, { role: role.value === 'admin' ? 'student' : role.value, username: '', name: '', password: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = true
  Object.assign(form, { role: row.role, username: row.username, name: row.name, password: '' })
  dialogVisible.value = true
}

async function onSubmit() {
  if (!form.username || !form.name) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  if (!editing.value && !form.password) {
    ElMessage.warning('请设置密码')
    return
  }
  if (editing.value) {
    await updateUser(users.value.find((u) => u.username === form.username)?.id, {
      name: form.name,
      ...(form.password ? { password: form.password } : {}),
    })
  } else {
    await createUser({
      role: form.role,
      username: form.username,
      name: form.name,
      password: form.password,
    })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  load()
}

async function toggleStatus(row) {
  await updateUser(row.id, { status: row.status === 'active' ? 'disabled' : 'active' })
  ElMessage.success(row.status === 'active' ? '已禁用' : '已启用')
  load()
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户「${row.name}」？删除后不可恢复。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteUserApi(row.id)
    ElMessage.success('删除成功')
    load()
  } catch {
    /* 拦截器已提示（存在关联数据时提示改用禁用） */
  }
}

onMounted(load)
</script>
