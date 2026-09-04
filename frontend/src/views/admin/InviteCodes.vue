<template>
  <div class="page admin-invite-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">注册邀请码管理</h1>
        <p class="header-desc">生成、分发并管控各类角色账户的一次性注册邀请码，防止未授权用户自行创建账户。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>生成新邀请码
      </el-button>
    </div>

    <div class="table-card">
      <div class="filter-bar">
        <el-radio-group v-model="role" @change="load">
          <el-radio-button value="">全部角色</el-radio-button>
          <el-radio-button value="student">学生</el-radio-button>
          <el-radio-button value="teacher">班主任</el-radio-button>
          <el-radio-button value="subject_teacher">任课老师</el-radio-button>
          <el-radio-button value="deyu_director">德育主任</el-radio-button>
          <el-radio-button value="consultant">咨询老师</el-radio-button>
          <el-radio-button value="parent">家长</el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="codes" v-loading="loading" empty-text="暂无邀请码记录" style="width: 100%">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column prop="code" label="邀请码" width="160">
          <template #default="{ row }">
            <code class="invite-code-text">{{ row.code }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="适用角色" width="120">
          <template #default="{ row }">
            <span class="role-badge">{{ roleLabel(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="当前状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="有效期至" min-width="170">
          <template #default="{ row }">
            <span :class="{ 'expired-text': isExpired(row.expires_at) }">{{ formatExpire(row.expires_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="生成时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="copyCode(row.code)">复制码</el-button>
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
    </div>

    <el-dialog v-model="dialogVisible" title="生成邀请码" width="420px">
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">班主任</el-radio>
            <el-radio value="subject_teacher">任课老师</el-radio>
            <el-radio value="deyu_director">德育主任</el-radio>
            <el-radio value="consultant">咨询老师</el-radio>
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
import { Plus } from '@element-plus/icons-vue'
import { listInviteCodes, createInviteCode, disableInviteCode } from '../../api/admin'

const codes = ref([])
const role = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ role: 'student', expires_at: null })

function roleLabel(r) {
  return { teacher: '班主任', subject_teacher: '任课老师', deyu_director: '德育主任', consultant: '咨询老师', student: '学生', parent: '家长' }[r] || r
}
function statusLabel(s) {
  return { active: '可用', used: '已使用', disabled: '已停用' }[s] || s
}
function statusType(s) {
  return { active: 'success', used: 'info', disabled: 'danger' }[s] || 'info'
}
function isExpired(val) {
  return val && new Date(val) < new Date()
}
function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
function formatExpire(val) {
  if (!val) return '永久有效'
  return formatTime(val)
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

<style scoped>
.admin-invite-page {
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

.filter-bar {
  margin-bottom: 16px;
}

.invite-code-text {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  font-weight: 700;
  color: #1e40af;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 6px;
  letter-spacing: 1px;
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

.expired-text {
  color: #ef4444;
}
</style>
