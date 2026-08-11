<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">题库</span>
      <el-button type="primary" @click="openCreate">新建题目</el-button>
    </div>

    <el-table :data="questions" v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="题型" width="90">
        <template #default="{ row }">{{ typeLabel(row.question_type) }}</template>
      </el-table-column>
      <el-table-column prop="content" label="内容" show-overflow-tooltip />
      <el-table-column prop="score" label="分数" width="80" />
      <el-table-column prop="difficulty" label="难度" width="80">
        <template #default="{ row }">{{ (row.difficulty * 100).toFixed(0) }}%</template>
      </el-table-column>
    </el-table>

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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createQuestion, kpTree as fetchKpTree, listQuestions } from '../../api/questions'

const questions = ref([])
const kpTree = ref([])
const kpTreeRef = ref()
const loading = ref(false)
const saving = ref(false)
const createVisible = ref(false)

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
