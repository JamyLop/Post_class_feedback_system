<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <span class="page-title">{{ assignment.title }}</span>
      <div>
        <el-button @click="loadSubmissions">我的提交</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交作业</el-button>
      </div>
    </div>

    <el-alert
      v-if="mySubmissions.length"
      type="info"
      :closable="false"
      style="margin-bottom: 16px"
    >
      最近提交：第 {{ mySubmissions[0].id }} 次，状态
      {{ { submitted: '已提交', processing: '处理中', failed: '失败' }[mySubmissions[0].status] || mySubmissions[0].status }}
    </el-alert>

    <el-tabs v-model="tab">
      <el-tab-pane label="文本作答" name="text">
        <el-card v-for="(q, i) in assignment.questions" :key="q.id" style="margin-bottom: 12px">
          <div class="q-head">
            <span>第 {{ i + 1 }} 题（{{ q.score }} 分 · {{ typeLabel(q.question_type) }}）</span>
          </div>
          <div class="q-content">{{ q.content }}</div>
          <el-input
            v-model="textAnswers[q.id]"
            type="textarea"
            :rows="2"
            placeholder="请输入本题答案"
            style="margin-top: 8px"
          />
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="图片 / PDF 上传" name="file">
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          accept="image/*,.pdf"
          :on-change="(f) => (file = f.raw)"
        >
          <el-icon style="font-size: 40px; color: #909399"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持图片或 PDF，提交后由系统 OCR 识别</div>
          </template>
        </el-upload>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="historyVisible" title="我的提交" width="600px">
      <el-table :data="mySubmissions">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ { text: '文本', image: '图片', pdf: 'PDF' }[row.content_type] }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">{{ row.status }}</template>
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
.q-head {
  font-weight: 600;
  margin-bottom: 8px;
}
.q-content {
  white-space: pre-wrap;
  color: #303133;
}
</style>
