<template>
  <div class="page questions-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">校本学科题库</h1>
        <p class="header-desc">维护各学科题目资源、标准答案与难度系数，支持 AI 智能解析录入。</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" plain @click="parseDialog.open()">
          <el-icon><Cpu /></el-icon>AI 智能解析录入
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>手工新建题目
        </el-button>
      </div>
    </div>

    <div class="table-card">
      <el-table :data="questions" v-loading="loading" empty-text="题库暂无题目" style="width: 100%">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="题型" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ typeLabel(row.question_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="题目内容" min-width="260" show-overflow-tooltip />
        <el-table-column prop="score" label="分值" width="90">
          <template #default="{ row }">
            <strong>{{ row.score }}</strong> 分
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度系数" width="110">
          <template #default="{ row }">
            <span class="diff-badge">{{ (row.difficulty * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createVisible" title="新建题目" width="720px">
      <el-form :model="form" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="科目">
              <el-select v-model="form.subject" style="width: 100%">
                <el-option label="数学" value="数学" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="年级">
              <el-select v-model="form.grade" style="width: 100%">
                <el-option label="初中" value="初中" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="题型">
          <el-select v-model="form.question_type" style="width: 100%">
            <el-option v-for="(v, k) in typeLabels" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="题目内容">
          <el-input v-model="form.content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="标准答案">
          <el-input v-model="form.standard_answer" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="分数">
              <el-input-number v-model="form.score" :min="0" :step="1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="难度">
              <el-input-number v-model="form.difficulty" :min="0" :max="1" :step="0.1" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="知识点">
          <el-tree
            ref="kpTreeRef"
            :data="kpTree"
            show-checkbox
            node-key="id"
            :props="{ label: 'name', children: 'children' }"
            default-expand-all
            style="max-height: 220px; overflow: auto; width: 100%; border: 1px solid #eee; padding: 8px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>

    <AiParseDialog ref="parseDialog" @created="load" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createQuestion, kpTree as fetchKpTree, listQuestions } from '../../api/questions'
import AiParseDialog from './AiParseDialog.vue'

const questions = ref([])
const kpTree = ref([])
const kpTreeRef = ref()
const loading = ref(false)
const saving = ref(false)
const createVisible = ref(false)
const parseDialog = ref()

const typeLabels = {
  single_choice: '单选', multiple_choice: '多选', judge: '判断',
  fill: '填空', calculation: '计算', short_answer: '简答',
}
const typeLabel = (t) => typeLabels[t] || t

const form = reactive({
  subject: '数学',
  grade: '初中',
  question_type: 'calculation',
  content: '',
  standard_answer: '',
  score: 10,
  difficulty: 0.5,
})

async function load() {
  loading.value = true
  try {
    questions.value = await listQuestions()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, {
    subject: '数学', grade: '初中', question_type: 'calculation',
    content: '', standard_answer: '', score: 10, difficulty: 0.5,
  })
  createVisible.value = true
}

async function onCreate() {
  if (!form.content) {
    ElMessage.warning('请填写题目内容')
    return
  }
  const checked = kpTreeRef.value?.getCheckedKeys() || []
  const halfChecked = kpTreeRef.value?.getHalfCheckedKeys() || []
  saving.value = true
  try {
    await createQuestion({
      ...form,
      knowledge_points: [...checked, ...halfChecked].map((id) => ({ id, weight: 1.0 })),
    })
    ElMessage.success('题目创建成功')
    createVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await load()
  kpTree.value = await fetchKpTree()
})
</script>

<style scoped>
.questions-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
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

.header-actions {
  display: flex;
  gap: 10px;
}

.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
  padding: 16px 18px;
}

.diff-badge {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 6px;
  font-family: monospace;
}
</style>
