<template>
  <div class="page admin-guardian-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">家长与学生关联管理</h1>
        <p class="header-desc">建立家长账户与在校学生的对应关系，家长仅可查看该学生经班主任发布的综合学情档案。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>新增家长关联
      </el-button>
    </div>

    <div class="table-card">
      <el-table :data="links" v-loading="loading" empty-text="暂无家长学生关联记录" style="width: 100%">
        <el-table-column label="家长账号" min-width="160">
          <template #default="{ row }"><span class="name-text">{{ row.parent_name }}</span></template>
        </el-table-column>
        <el-table-column label="关联学生" min-width="160">
          <template #default="{ row }"><span class="name-text">{{ row.student_name }}</span></template>
        </el-table-column>
        <el-table-column prop="relationship" label="关系类型" width="120">
          <template #default="{ row }">
            <span class="relation-badge">{{ relationshipLabel(row.relationship) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联建立时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="remove(row)">解除关联</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="visible" title="新增家长学生关联" width="460px">
      <el-form label-position="top">
        <el-form-item label="家长账号">
          <el-select v-model="form.parent_id" filterable placeholder="选择家长账号" style="width: 100%">
            <el-option v-for="item in parents" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生账号">
          <el-select v-model="form.student_id" filterable placeholder="选择学生" style="width: 100%">
            <el-option v-for="item in students" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关系类型">
          <el-select v-model="form.relationship" style="width: 100%">
            <el-option label="父亲" value="father" />
            <el-option label="母亲" value="mother" />
            <el-option label="法定监护人" value="guardian" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存关联</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createGuardianLink, deleteGuardianLink, listGuardianLinks } from '../../api/admin'
import { listUsers } from '../../api/users'

const links = ref([])
const parents = ref([])
const students = ref([])
const loading = ref(false)
const visible = ref(false)
const form = reactive({ parent_id: null, student_id: null, relationship: 'guardian' })

const relationshipLabel = (value) => ({ father: '父亲', mother: '母亲', guardian: '法定监护人' }[value] || value)

function formatTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function load() {
  loading.value = true
  try {
    links.value = await listGuardianLinks()
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  Object.assign(form, { parent_id: null, student_id: null, relationship: 'guardian' })
  ;[parents.value, students.value] = await Promise.all([listUsers('parent'), listUsers('student')])
  visible.value = true
}

async function save() {
  if (!form.parent_id || !form.student_id) return ElMessage.warning('请选择家长账号和学生')
  await createGuardianLink({ ...form })
  ElMessage.success('家长关联已建立')
  visible.value = false
  load()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认解除「${row.parent_name}」与「${row.student_name}」的家长关联？`,
      '解除关联',
      { type: 'warning' }
    )
  } catch {
    return
  }
  await deleteGuardianLink(row.id)
  ElMessage.success('关联已解除')
  load()
}

onMounted(load)
</script>

<style scoped>
.admin-guardian-page {
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

.name-text {
  font-size: 14px;
  font-weight: 650;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.relation-badge {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 6px;
}
</style>
