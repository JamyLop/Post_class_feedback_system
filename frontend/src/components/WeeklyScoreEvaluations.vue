<template>
  <div class="weekly-evaluations">
    <div v-for="item in score.evaluations || []" :key="item.id" class="evaluation">
      <div class="evaluation-meta">
        <strong>{{ item.teacher_name }}</strong>
        <span>{{ item.teacher_role === 'head_teacher' ? '班主任' : '学科老师' }}</span>
        <time>{{ formatTime(item.updated_at) }}</time>
      </div>
      <p>{{ item.content }}</p>
    </div>
    <span v-if="!score.evaluations?.length" class="empty">暂无评价</span>
    <el-button v-if="score.can_evaluate" link type="primary" @click="openEditor">
      {{ ownEvaluation ? '修改我的评价' : '添加评价' }}
    </el-button>
    <el-dialog v-model="visible" title="周测评价" width="min(520px, 92vw)" append-to-body :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving">
      <p class="exam-context">{{ score.student_name }} · {{ score.subject }} · {{ score.exam_name || score.exam_date }} · {{ score.score }} / {{ score.max_score }}</p>
      <el-form label-position="top" @submit.prevent="save">
        <el-form-item label="评价内容">
          <el-input v-model="content" type="textarea" :rows="5" maxlength="2000" show-word-limit :disabled="saving" placeholder="填写本次周测表现、需改进的问题和学习建议" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="saving" @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!content.trim()" @click="save">保存评价</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { saveWeeklyEvaluation } from '../api/weeklyScores'

const props = defineProps({ score: { type: Object, required: true } })
const emit = defineEmits(['saved'])
const auth = useAuthStore()
const visible = ref(false)
const saving = ref(false)
const content = ref('')
const ownEvaluation = computed(() => props.score.evaluations?.find(item => item.teacher_id === auth.user?.id))

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : ''
}

function openEditor() {
  content.value = ownEvaluation.value?.content || ''
  visible.value = true
}

async function save() {
  if (saving.value || !content.value.trim()) return
  saving.value = true
  try {
    const updated = await saveWeeklyEvaluation(props.score.id, { content: content.value.trim() })
    emit('saved', updated)
    visible.value = false
    ElMessage.success('评价已保存')
  } catch (error) {
    const detail = error?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '评价保存失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.weekly-evaluations { display: grid; gap: 8px; padding: 6px 0; }
.evaluation + .evaluation { border-top: 1px solid var(--line); padding-top: 8px; }
.evaluation-meta { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; font-size: 12px; }
.evaluation-meta span, .evaluation-meta time, .empty { color: var(--ink-muted); font-size: 12px; }
.evaluation p { white-space: pre-wrap; overflow-wrap: anywhere; margin: 4px 0 0; line-height: 1.6; }
.weekly-evaluations > .el-button { justify-self: start; margin: 0; }
.exam-context { color: var(--ink-secondary); margin: 0 0 16px; line-height: 1.6; }
</style>
