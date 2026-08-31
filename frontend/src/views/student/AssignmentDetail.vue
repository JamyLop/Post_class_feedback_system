<template>
  <div class="page student-answer-page" v-loading="loading">
    <div class="page-header">
      <div>
        <el-button link class="back-btn" @click="$router.push('/student/assignments')">
          <el-icon><ArrowLeft /></el-icon>返回作业列表
        </el-button>
        <h1 class="page-title">{{ assignment.title || '加载中...' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="loadSubmissions">提交记录</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交作业</el-button>
      </div>
    </div>

    <el-alert
      v-if="mySubmissions.length"
      type="info"
      :closable="false"
      style="margin-bottom: 4px"
    >
      最近提交：第 {{ mySubmissions[0].id }} 次 · 状态：
      <strong>{{ { submitted: '已提交等待批改', processing: '处理中', failed: '处理失败' }[mySubmissions[0].status] || mySubmissions[0].status }}</strong>
    </el-alert>

    <div class="answer-surface">
      <el-tabs v-model="tab">
        <el-tab-pane label="📝 逐题文本作答" name="text">
          <div class="questions-list">
            <el-card
              v-for="(q, i) in assignment.questions"
              :key="q.id"
              shadow="never"
              class="question-card"
            >
              <div class="q-head">
                <span class="q-index">第 {{ i + 1 }} 题</span>
                <span class="q-meta">{{ typeLabel(q.question_type) }} · {{ q.score }} 分</span>
              </div>
              <div class="q-content">{{ q.content }}</div>
              <el-input
                v-model="textAnswers[q.id]"
                type="textarea"
                :rows="3"
                placeholder="请在此填写本题解答..."
                style="margin-top: 10px"
              />
            </el-card>
          </div>
        </el-tab-pane>
        <el-tab-pane label="📎 图片 / PDF 整份上传" name="file">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept="image/*,.pdf"
            :on-change="(f) => (file = f.raw)"
            class="upload-area"
          >
            <el-icon style="font-size: 44px; color: #94a3b8"><UploadFilled /></el-icon>
            <div class="el-upload__text">将作业文件拖拽至此，或 <em>点击选择文件</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 JPG / PNG / PDF，系统将通过 AI-OCR 自动识别内容</div>
            </template>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="historyVisible" title="我的提交记录" width="600px">
      <el-table :data="mySubmissions" empty-text="暂无提交记录">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="提交方式" width="100">
          <template #default="{ row }">{{ { text: '文本', image: '图片', pdf: 'PDF' }[row.content_type] }}</template>
        </el-table-column>
        <el-table-column label="批改状态" width="130">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="提交时间" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { getAssignment } from '../../api/assignments'
import { listSubmissions, submitAssignment } from '../../api/submissions'

const route = useRoute()
const assignment = ref({})
const loading = ref(false)
const submitting = ref(false)
const tab = ref('text')
const file = ref(null)
const textAnswers = reactive({})
const mySubmissions = ref([])
const historyVisible = ref(false)

const typeLabel = (t) => ({
  single_choice: '单选', multiple_choice: '多选', judge: '判断',
  fill: '填空', calculation: '计算', short_answer: '简答',
}[t] || t)

async function load() {
  loading.value = true
  try {
    assignment.value = await getAssignment(route.params.id)
    for (const q of assignment.value.questions || []) {
      if (textAnswers[q.id] === undefined) textAnswers[q.id] = ''
    }
  } finally {
    loading.value = false
  }
}

async function loadSubmissions() {
  mySubmissions.value = await listSubmissions(route.params.id)
  historyVisible.value = true
}

async function onSubmit() {
  const fd = new FormData()
  if (tab.value === 'text') {
    const answers = (assignment.value.questions || [])
      .map((q) => ({ question_id: q.id, student_answer: textAnswers[q.id] || '' }))
      .filter((a) => a.student_answer)
    if (!answers.length) {
      ElMessage.warning('请至少作答一题')
      return
    }
    fd.append('content_type', 'text')
    fd.append('answers_json', JSON.stringify(answers))
    fd.append('content_text', answers.map((a) => a.student_answer).join('\n'))
  } else {
    if (!file.value) {
      ElMessage.warning('请先上传文件')
      return
    }
    const isPdf = file.value.type === 'application/pdf' || /\.pdf$/i.test(file.value.name)
    fd.append('content_type', isPdf ? 'pdf' : 'image')
    fd.append('file', file.value)
  }
  submitting.value = true
  try {
    await submitAssignment(route.params.id, fd)
    ElMessage.success('提交成功')
    file.value = null
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.student-answer-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  margin: 4px 0 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
}

.header-actions {
  display: flex;
  gap: 10px;
}

.answer-surface {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  padding: 20px;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.question-card {
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
}

.q-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.q-index {
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
}

.q-meta {
  font-size: 12px;
  color: #64748b;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 6px;
}

.q-content {
  white-space: pre-wrap;
  color: #334155;
  line-height: 1.65;
  font-size: 14px;
}
</style>
