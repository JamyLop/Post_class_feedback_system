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

    <el-dialog v-model="dialogVisible" title="添加学生到本班级" width="560px" @close="onDialogClose">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="新建学生" name="create">
          <el-alert type="info" :closable="false" show-icon title="仅需录入学生档案信息，账号由系统自动生成" style="margin-bottom: 14px" />
          <el-form :model="newForm" label-width="92px" @submit.prevent>
            <el-form-item label="姓名" required>
              <el-input v-model="newForm.name" placeholder="请输入学生姓名" maxlength="64" />
            </el-form-item>
            <el-form-item label="性别">
              <el-select v-model="newForm.gender" clearable placeholder="请选择" style="width: 100%">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
            <el-form-item label="民族">
              <el-input v-model="newForm.ethnicity" placeholder="例如：汉族" maxlength="32" />
            </el-form-item>
            <el-form-item label="年级">
              <el-input v-model="newForm.grade" placeholder="例如：高三" maxlength="32" />
            </el-form-item>
            <el-form-item label="生源地学校">
              <el-input v-model="newForm.source_school" placeholder="填写学生原就读学校" maxlength="128" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="选择已有学生" name="existing">
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
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <template v-if="activeTab === 'create'">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="creating" class="no-wrap-btn" @click="onCreateAndAdd">新建并加入班级</el-button>
        </template>
        <template v-else>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :disabled="!selected.length" class="no-wrap-btn" @click="onAdd">添加选中学生 ({{ selected.length }})</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { addStudents, listStudents, listUsers, createStudentAndAdd, getClass } from '../../api/classes'

const route = useRoute()
const classId = route.params.id
const students = ref([])
const candidates = ref([])
const keyword = ref('')
const selected = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const activeTab = ref('create')
const creating = ref(false)
const classInfo = ref(null)
const newForm = reactive({ name: '', gender: '', ethnicity: '', grade: '', source_school: '' })

async function load() {
  loading.value = true
  try {
    const [list, cls] = await Promise.all([listStudents(classId), getClass(classId).catch(() => null)])
    students.value = list
    if (cls) classInfo.value = cls
    // 预填年级默认值
    if (cls?.grade && !newForm.grade) newForm.grade = cls.grade
  } finally {
    loading.value = false
  }
}

async function openAddDialog() {
  activeTab.value = 'create'
  dialogVisible.value = true
  keyword.value = ''
  selected.value = []
  candidates.value = await listUsers('student', '')
  Object.assign(newForm, { name: '', gender: '', ethnicity: '', grade: classInfo.value?.grade || '', source_school: '' })
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

async function onCreateAndAdd() {
  if (!newForm.name.trim()) {
    ElMessage.warning('请填写学生姓名')
    return
  }
  creating.value = true
  try {
    await createStudentAndAdd(classId, {
      name: newForm.name.trim(),
      gender: newForm.gender || '',
      ethnicity: newForm.ethnicity?.trim() || '',
      grade: newForm.grade?.trim() || '',
      source_school: newForm.source_school?.trim() || '',
    })
    ElMessage.success('新建学生并加入班级成功，账号已自动生成')
    dialogVisible.value = false
    Object.assign(newForm, { name: '', gender: '', ethnicity: '', grade: classInfo.value?.grade || '', source_school: '' })
    load()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function onDialogClose() {
  selected.value = []
  creating.value = false
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

.no-wrap-btn {
  white-space: nowrap;
}

:deep(.el-form-item__label) {
  white-space: nowrap;
}
</style>
