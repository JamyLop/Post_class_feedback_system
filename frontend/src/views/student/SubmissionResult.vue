<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <span class="page-title">提交结果</span>
      <el-button @click="$router.push('/student/assignments')">返回作业列表</el-button>
    </div>
    <el-card v-if="submission">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="提交ID">{{ submission.id }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ { text: '文本', image: '图片', pdf: 'PDF' }[submission.content_type] }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusMap[submission.status] || 'info'">{{ statusLabel(submission.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ submission.submitted_at }}</el-descriptions-item>
        <el-descriptions-item label="文件" :span="2">
          <el-button v-if="submission.content_url" link type="primary" @click="openSubmissionFile(submission.content_url)">查看提交文件</el-button>
          <span v-else>—</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="grading" style="margin-top: 16px">
      <template #header>
        <span>AI 批改结果</span>
        <el-tag v-if="grading.status === 'ai_graded'" type="success" style="margin-left: 8px">总分 {{ grading.total_score }} / {{ grading.max_total }}</el-tag>
      </template>
      <el-table :data="grading.answers" border>
        <el-table-column label="题号" width="70">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="题型" width="90">
          <template #default="{ row }">{{ typeLabel(row.question_type) }}</template>
        </el-table-column>
        <el-table-column prop="content" label="题目" />
        <el-table-column prop="student_answer" label="我的答案" width="180" show-overflow-tooltip />
        <el-table-column label="得分" width="90">
          <template #default="{ row }">
            <span :class="row.is_correct === false ? 'wrong' : ''">{{ row.score ?? '—' }} / {{ row.max_score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="AI评语" width="220">
          <template #default="{ row }">
            <div v-if="row.grading">
              <el-tag :type="confTag(row.grading.confidence)" size="small">{{ (row.grading.confidence * 100).toFixed(0) }}%</el-tag>
              <span style="margin-left: 6px">{{ row.grading.ai_comment }}</span>
            </div>
            <span v-else>批改中…</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getSubmission, getSubmissionGrading, openSubmissionFile } from '../../api/submissions'

const route = useRoute()
const submission = ref(null)
const grading = ref(null)
const loading = ref(false)
const statusMap = {
  submitted: 'info', processing: 'warning', ai_graded: 'success',
  teacher_reviewed: 'success', completed: 'success', failed: 'danger',
}
const statusLabel = (s) => ({
  submitted: '已提交', processing: '处理中', ai_graded: 'AI已批改',
  teacher_reviewed: '待复核', completed: '已完成', failed: '失败',
}[s] || s)
const typeLabel = (t) => ({
  single_choice: '单选', multiple_choice: '多选', judge: '判断',
  fill: '填空', calculation: '计算', short_answer: '简答',
}[t] || t)
const confTag = (c) => (c >= 0.85 ? 'success' : c >= 0.7 ? 'warning' : 'danger')

async function load() {
  loading.value = true
  try {
    submission.value = await getSubmission(route.params.id)
    try {
      grading.value = await getSubmissionGrading(route.params.id)
    } catch (e) {
      // 批改尚未完成时忽略
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.wrong {
  color: #f56c6c;
  font-weight: 600;
}
</style>
