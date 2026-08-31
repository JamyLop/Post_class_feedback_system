<template>
  <div class="page class-students-page">
    <div class="back-bar">
      <el-button link @click="$router.push('/teacher/classes')">
        <el-icon><ArrowLeft /></el-icon>返回班级列表
      </el-button>
    </div>

    <div class="page-header">
      <div>
        <h1 class="page-title">班级学生名册</h1>
        <p class="header-desc">查看与配置当前班级已加入的学生成员名单。</p>
      </div>
      <el-button type="primary" @click="openAddDialog">
        <el-icon><Plus /></el-icon>添加学生
      </el-button>
    </div>

    <div class="table-card">
      <el-table :data="students" v-loading="loading" empty-text="当前班级暂无学生">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="学生姓名" min-width="180">
          <template #default="{ row }">
            <div class="student-user-cell">
              <span class="user-avatar">{{ row.name?.slice(0, 1) || '学' }}</span>
              <div>
                <strong>{{ row.name }}</strong>
                <small>{{ row.username }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="登录账号 / 学号" min-width="160" />
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="添加学生到本班级" width="520px">
      <el-input v-model="keyword" placeholder="搜索学生用户名 / 姓名" clearable style="margin-bottom: 14px" @input="onSearch" />
      <el-table
        :data="candidates"
        height="320"
        empty-text="输入关键词搜索学生"
        @selection-change="(rows) => (selected = rows)"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="username" label="登录用户名" />
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selected.length" @click="onAdd">添加选中学生 ({{ selected.length }})</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
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

async function openAddDialog() {
  dialogVisible.value = true
  keyword.value = ''
  selected.value = []
  candidates.value = await listUsers('student', '')
}

async function onSearch() {
  candidates.value = await listUsers('student', keyword.value)
}

async function onAdd() {
  try {
    await addStudents(classId, selected.value.map((s) => s.id))
    ElMessage.success('添加成功')
    dialogVisible.value = false
    load()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  }
}

onMounted(load)
</script>

<style scoped>
.class-students-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-bar {
  margin-bottom: -4px;
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

.student-user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  font-weight: 600;
  font-size: 12px;
}

.student-user-cell strong {
  font-size: 13.5px;
  color: var(--ink);
}

.student-user-cell small {
  display: block;
  font-size: 11px;
  color: #94a3b8;
}
</style>
