<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">提交记录</span>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    <el-table :data="submissions" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="student_id" label="学生ID" width="100" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ { text: '文本', image: '图片', pdf: 'PDF' }[row.content_type] || row.content_type }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status] || 'info'">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="AI批改" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'ai_graded'" type="success">已批改</el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="submitted_at" label="提交时间" />
      <el-table-column label="文件" width="100">
        <template #default="{ row }">
          <el-button v-if="row.content_url" link type="primary" @click="openSubmissionFile(row.content_url)">查看</el-button>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="row.status !== 'ai_graded'" @click="openGrading(row)">批改结果</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawer" :title="'批改详情 #' + current.id" size="70%">
      <template v-if="grading">
        <el-descriptions :column="3" border style="margin-bottom: 16px">
          <el-descriptions-item label="总分">{{ grading.total_score }} / {{ grading.max_total }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusMap[grading.status] || 'info'">{{ statusLabel(grading.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-table :data="grading.answers" border>
          <el-table-column label="题号" width="60">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column label="题型" width="80">
            <template #default="{ row }">{{ typeLabel(row.question_type) }}</template>
          </el-table-column>
          <el-table-column prop="content" label="题目" />
          <el-table-column prop="student_answer" label="学生答案" width="160" show-overflow-tooltip />
          <el-table-column prop="standard_answer" label="标准答案" width="160" show-overflow-tooltip />
          <el-table-column label="得分" width="80">
            <template #default="{ row }">{{ row.score ?? '—' }} / {{ row.max_score }}</template>
          </el-table-column>
          <el-table-column label="错误类型" width="100">
            <template #default="{ row }">{{ row.grading?.error_type || '—' }}</template>
          </el-table-column>
          <el-table-column label="AI评语" width="220">
            <template #default="{ row }">
              <div v-if="row.grading">
                <el-tag :type="confTag(row.grading.confidence)" size="small">{{ (row.grading.confidence * 100).toFixed(0) }}%</el-tag>
                <span style="margin-left: 6px">{{ row.grading.ai_comment }}</span>
              </div>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button v-if="row.grading" link type="warning" @click="onRetry(row.grading.id)">重新批改</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSubmissionGrading, listSubmissions, openSubmissionFile, retryGrading } from '../../api/submissions'

const route = useRoute()
const submissions = ref([])
const loading = ref(false)
const drawer = ref(false)
const current = ref({})
const grading = ref(null)
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

async function openGrading(row) {
  current.value = row
  drawer.value = true
  grading.value = null
  grading.value = await getSubmissionGrading(row.id)
}

async function onRetry(gradingId) {
  try {
    grading.value = await retryGrading(gradingId)
    ElMessage.success('已重新批改')
  } catch (e) {
    ElMessage.error('重试失败')
  }
}

async function load() {
  loading.value = true
  try {
    submissions.value = await listSubmissions(route.params.id)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
