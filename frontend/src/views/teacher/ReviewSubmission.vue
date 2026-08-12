<template>
  <div class="page" v-if="grading">
    <div class="page-header">
      <span class="page-title">复核作业 #{{ grading.submission_id }}</span>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    <el-card class="head-card" shadow="never">
      <div class="head-row">
        <span>学生：{{ studentName }}</span>
        <span>作业：{{ assignmentTitle }}</span>
        <span>
          总分：
          <b>{{ grading.total_score }}</b> / {{ grading.max_total }}
        </span>
        <el-tag :type="grading.status === 'teacher_reviewed' ? 'success' : 'warning'">
          {{ grading.status === 'teacher_reviewed' ? '已全部确认' : '待复核' }}
        </el-tag>
        <span class="spacer" />
        <el-button type="primary" :disabled="allConfirmed" @click="onConfirmAll">确认全部批改</el-button>
      </div>
    </el-card>

    <el-row :gutter="12">
      <el-col :span="7">
        <el-card shadow="never" class="nav-card">
          <div
            v-for="(a, i) in grading.answers"
            :key="a.answer_id"
            class="nav-item"
            :class="{ active: i === index, confirmed: a.grading?.status === 'confirmed' }"
            @click="goTo(i)"
          >
            <el-icon v-if="a.grading?.status === 'confirmed'" color="#67c23a"><CircleCheck /></el-icon>
            <el-icon v-else color="#409eff"><Document /></el-icon>
            <span>第 {{ i + 1 }} 题 · {{ typeLabel(a.question_type) }}</span>
            <el-tag v-if="a.grading" size="small" :type="confTag(a.grading.confidence)">{{ pct(a.grading.confidence) }}</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="17">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <span>第 {{ index + 1 }} / {{ grading.answers.length }} 题</span>
              <div>
                <el-button :disabled="index <= 0" @click="goTo(index - 1)">上一题</el-button>
                <el-button :disabled="index >= grading.answers.length - 1" @click="goTo(index + 1)">下一题</el-button>
              </div>
            </div>
          </template>
          <template v-if="cur">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="题型">
                {{ typeLabel(cur.question_type) }}
                <el-tag v-if="cur.grading?.status === 'confirmed'" type="success" size="small" style="margin-left: 8px">已确认</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="题目">{{ cur.content }}</el-descriptions-item>
              <el-descriptions-item label="学生答案">
                <pre class="answer-pre">{{ cur.student_answer || cur.ocr_text || '（空）' }}</pre>
              </el-descriptions-item>
              <el-descriptions-item label="标准答案">{{ cur.standard_answer }}</el-descriptions-item>
            </el-descriptions>

            <el-divider content-position="left">AI 批改结果</el-divider>
            <el-descriptions :column="2" border v-if="cur.grading">
              <el-descriptions-item label="AI 分数">{{ cur.grading.ai_score ?? '—' }} / {{ cur.max_score }}</el-descriptions-item>
              <el-descriptions-item label="AI 置信度">
                <el-tag :type="confTag(cur.grading.confidence)">{{ pct(cur.grading.confidence) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="错误类型" :span="2">{{ cur.grading.error_type || '—' }}</el-descriptions-item>
              <el-descriptions-item label="AI 评语" :span="2">
                {{ cur.grading.ai_comment || '—' }}
                <el-tag v-if="cur.grading.teacher_comment && cur.grading.status === 'confirmed'" type="warning" size="small" style="margin-left: 8px">已改：{{ cur.grading.teacher_comment }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="错误位置" :span="2" v-if="errorPoints.length">
                <div v-for="(p, i) in errorPoints" :key="i">
                  {{ p.position }}：{{ p.description }}
                </div>
              </el-descriptions-item>
            </el-descriptions>
            <el-alert v-else type="info" :closable="false" title="该题暂无批改结果" />

            <el-divider content-position="left">教师复核</el-divider>
            <el-form label-width="90px">
              <el-form-item label="教师分数">
                <el-input-number
                  v-model="form.score"
                  :min="0"
                  :max="cur.max_score ?? 0"
                  :precision="1"
                />
              </el-form-item>
              <el-form-item label="教师评语">
                <el-input
                  v-model="form.comment"
                  type="textarea"
                  :rows="2"
                  placeholder="可选，作为最终评语"
                />
              </el-form-item>
            </el-form>

            <div class="actions">
              <el-button type="success" :disabled="!cur.grading" @click="onConfirm">
                {{ cur.grading?.status === 'confirmed' ? '保存修改' : '确认本题' }}
              </el-button>
              <el-button type="warning" @click="flagDialog = true">标记异常</el-button>
              <el-button v-if="cur.grading" @click="onRegrade">重新 AI 批改</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="flagDialog" title="标记异常" width="480px">
      <el-input v-model="flagComment" type="textarea" :rows="3" placeholder="请输入异常原因（必填）" />
      <template #footer>
        <el-button @click="flagDialog = false">取消</el-button>
        <el-button type="warning" @click="onFlag">提交</el-button>
      </template>
    </el-dialog>
  </div>
  <div v-else v-loading="loading" class="page">
    <el-empty description="加载中" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getSubmissionGrading, confirmGrading, flagGrading, retryGrading, confirmAllGrading,
} from '../../api/submissions'

const route = useRoute()
const loading = ref(false)
const grading = ref(null)
const index = ref(0)
const form = ref({ score: null, comment: '' })
const flagDialog = ref(false)
const flagComment = ref('')

const submissionId = route.params.submissionId

const typeLabel = (t) => ({
  single_choice: '单选', multiple_choice: '多选', judge: '判断',
  fill: '填空', calculation: '计算', short_answer: '简答',
}[t] || t)
const pct = (c) => `${Math.round((c || 0) * 100)}%`
const confTag = (c) => (c >= 0.85 ? 'success' : c >= 0.7 ? 'warning' : 'danger')
const cur = computed(() => grading.value?.answers[index.value])
const reviewRow = history.state?.row || {}
const studentName = reviewRow.student_name || '—'
const assignmentTitle = reviewRow.assignment_title || '—'
const errorPoints = computed(() => {
  const points = cur.value?.grading?.error_points
  return Array.isArray(points) ? points : []
})
const allConfirmed = computed(
  () => grading.value?.answers.every((a) => a.grading?.status === 'confirmed') ?? true,
)

function goTo(i) {
  index.value = i
  resetForm()
}

function resetForm() {
  const g = cur.value?.grading
  form.value = {
    score: g?.teacher_score ?? g?.ai_score ?? cur.value?.score ?? null,
    comment: g?.teacher_comment ?? '',
  }
}

async function load() {
  loading.value = true
  try {
    grading.value = await getSubmissionGrading(submissionId)
    resetForm()
  } finally {
    loading.value = false
  }
}

async function onConfirm() {
  const gid = cur.value?.grading?.id
  if (!gid) return
  try {
    grading.value = await confirmGrading(gid, {
      teacher_score: form.value.score,
      teacher_comment: form.value.comment,
    })
    ElMessage.success('已确认该题')
  } catch (e) {
    ElMessage.error('确认失败')
  }
}

async function onRegrade() {
  const gid = cur.value?.grading?.id
  if (!gid) return
  try {
    grading.value = await retryGrading(gid)
    ElMessage.success('已重新 AI 批改')
    resetForm()
  } catch (e) {
    ElMessage.error('重新批改失败')
  }
}

async function onFlag() {
  const gid = cur.value?.grading?.id
  if (!flagComment.value.trim()) {
    ElMessage.warning('请填写异常原因')
    return
  }
  try {
    grading.value = await flagGrading(gid, { teacher_comment: flagComment.value })
    flagDialog.value = false
    flagComment.value = ''
    ElMessage.success('已标记异常，保留待复核')
  } catch (e) {
    ElMessage.error('标记失败')
  }
}

async function onConfirmAll() {
  try {
    grading.value = await confirmAllGrading(submissionId)
    ElMessage.success('已确认全部批改')
  } catch (e) {
    ElMessage.error('确认失败')
  }
}

watch(cur, (_, old) => {
  if (old) resetForm()
})

onMounted(load)
</script>

<style scoped>
.head-card .head-row {
  display: flex;
  align-items: center;
  gap: 20px;
}
.spacer { flex: 1; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 6px;
}
.nav-item:hover { background: #f5f7fa; }
.nav-item.active { background: #ecf5ff; color: #409eff; }
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.answer-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.actions { margin-top: 8px; }
</style>