<template>
  <div class="page admin-users-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">全校用户与权限管理</h1>
        <p class="header-desc">统一维护学生、班主任、德育主任、家长与校级管理账号及账户启用状态。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>新建系统用户
      </el-button>
    </div>

    <div class="table-card">
      <div class="filter-toolbar">
        <el-radio-group v-model="role" @change="load">
          <el-radio-button value="student">学生 (在校)</el-radio-button>
          <el-radio-button value="teacher">任课与班主任</el-radio-button>
          <el-radio-button value="subject_teacher">任课老师</el-radio-button>
          <el-radio-button value="deyu_director">德育主任</el-radio-button>
          <el-radio-button value="consultant">咨询老师</el-radio-button>
          <el-radio-button value="parent">家长账户</el-radio-button>
          <el-radio-button value="admin">校级管理/校长</el-radio-button>
        </el-radio-group>

        <el-input
          v-model="keyword"
          placeholder="搜索账号 / 姓名..."
          clearable
          :prefix-icon="Search"
          style="width: 240px"
          @input="load"
        />
      </div>

      <el-table :data="users" v-loading="loading" empty-text="当前角色暂无用户" style="width: 100%">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="姓名 / 身份" min-width="160">
          <template #default="{ row }">
            <div>
              <span class="name-text">{{ row.name }}</span>
              <small class="username-text">{{ row.username }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="登录用户名" min-width="140" />
        <el-table-column prop="channel" label="渠道" min-width="120" />
        <el-table-column prop="role" label="系统角色" width="130">
          <template #default="{ row }">
            <span class="role-badge">{{ roleLabel(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="账号状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'" effect="plain">
              {{ row.status === 'active' ? '正常在用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="row.role === 'student' || row.role === 'teacher' || row.role === 'subject_teacher' || row.role === 'deyu_director' || row.role === 'consultant' || row.role === 'parent'"
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
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新建用户'" width="440px">
      <el-form :model="form" label-width="70px">
        <el-form-item label="角色">
          <el-radio-group v-model="form.role" :disabled="editing">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">班主任</el-radio>
            <el-radio value="subject_teacher">任课老师</el-radio>
            <el-radio value="deyu_director">德育主任</el-radio>
            <el-radio value="consultant">咨询老师</el-radio>
            <el-radio value="parent">家长</el-radio>
            <el-radio value="admin">校长</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="editing" placeholder="用户名（3-64位）" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="姓名" />
        </el-form-item>
        <el-form-item v-if="form.role === 'student'" label="渠道">
          <el-input v-model="form.channel" placeholder="生源渠道（选填）" />
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
import { Plus, Search } from '@element-plus/icons-vue'
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
const form = reactive({ role: 'student', username: '', name: '', password: '', channel: '' })

function roleLabel(r) {
  return { admin: '校长', teacher: '班主任', subject_teacher: '任课老师', deyu_director: '德育主任', consultant: '咨询老师', student: '学生', parent: '家长' }[r] || r
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
  Object.assign(form, { role: role.value === 'admin' ? 'student' : role.value, username: '', name: '', password: '', channel: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = true
  Object.assign(form, { role: row.role, username: row.username, name: row.name, password: '', channel: row.channel || '' })
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
      ...(form.role === 'student' ? { channel: form.channel || '' } : {}),
    })
  } else {
    await createUser({
      role: form.role,
      username: form.username,
      name: form.name,
      password: form.password,
      ...(form.role === 'student' ? { channel: form.channel || '' } : {}),
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

<style scoped>
.admin-users-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.header-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
}

.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
  padding: 16px 18px;
}

.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.name-text {
  font-size: 14px;
  font-weight: 650;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.username-text {
  display: block;
  font-size: 11.5px;
  color: #64748b;
  margin-top: 2px;
}

.role-badge {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 6px;
}
</style>
