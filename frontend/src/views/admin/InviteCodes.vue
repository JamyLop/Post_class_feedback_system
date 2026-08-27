<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">邀请码管理</span>
      <el-button type="primary" @click="openCreate">生成邀请码</el-button>
    </div>

    <el-radio-group v-model="role" style="margin-bottom: 12px" @change="load">
      <el-radio-button value="">全部</el-radio-button>
      <el-radio-button value="student">学生</el-radio-button>
      <el-radio-button value="teacher">教师</el-radio-button>
      <el-radio-button value="parent">家长</el-radio-button>
    </el-radio-group>

    <el-table :data="codes" v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="code" label="邀请码" width="140">
        <template #default="{ row }">
          <el-tag>{{ row.code }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="90">
        <template #default="{ row }">{{ roleLabel(row.role) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="expires_at" label="有效期至" width="200">
        <template #default="{ row }">{{ row.expires_at || '永久有效' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="200" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="copyCode(row.code)">复制</el-button>
          <el-button
            v-if="row.status === 'active'"
            link
            type="warning"
            @click="onDisable(row)"
          >
            停用
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="生成邀请码" width="420px">
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">教师</el-radio>
            <el-radio value="parent">家长</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="有效期至">
          <el-date-picker
            v-model="form.expires_at"
            type="datetime"
            placeholder="留空则永久有效"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onCreate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listInviteCodes, createInviteCode, disableInviteCode } from '../../api/admin'

const codes = ref([])
const role = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ role: 'student', expires_at: null })

function roleLabel(r) {
  return { teacher: '教师', student: '学生', parent: '家长' }[r] || r
}
function statusLabel(s) {
  return { active: '未使用', used: '已使用', disabled: '已停用' }[s] || s
}
function statusType(s) {
  return { active: 'success', used: 'info', disabled: 'danger' }[s] || 'info'
}

async function load() {
  loading.value = true
  try {
    codes.value = await listInviteCodes(role.value)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.role = 'student'
  form.expires_at = null
  dialogVisible.value = true
}

async function onCreate() {
  await createInviteCode({
    role: form.role,
    ...(form.expires_at ? { expires_at: form.expires_at.toISOString() } : {}),
  })
  ElMessage.success('生成成功')
  dialogVisible.value = false
  load()
}

function copyCode(code) {
  navigator.clipboard?.writeText(code)
  ElMessage.success('已复制')
}

async function onDisable(row) {
  await disableInviteCode(row.id)
  ElMessage.success('已停用')
  load()
}

onMounted(load)
</script>
