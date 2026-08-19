<template>
  <el-dialog v-model="visible" title="代学生提交作业" width="720px" :close-on-click-modal="false">
    <el-form :model="form" label-width="90px">
      <el-form-item label="学生">
        <el-select v-model="form.student_id" filterable placeholder="选择班级中的学生" style="width: 100%">
          <el-option
            v-for="s in students"
            :key="s.id"
            :label="`${s.name}（${s.username}）`"
            :value="s.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="提交方式">
        <el-radio-group v-model="form.content_type">
          <el-radio-button value="text">文字作答</el-radio-button>
          <el-radio-button value="image">图片上传</el-radio-button>
          <el-radio-button value="pdf">PDF 上传</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <template v-if="form.content_type === 'text'">
        <el-form-item label="作答内容">
          <el-input v-model="form.content_text" type="textarea" :rows="6" placeholder="粘贴学生作业文字内容（逐题作答）" />
        </el-form-item>
        <div v-if="assignment.questions && assignment.questions.length" style="margin-bottom: 12px">
          <div style="margin-bottom: 8px; color: #606266; font-size: 13px">按题作答（可留空，留空则用上方整卷文字）：</div>
          <el-form-item v-for="q in assignment.questions" :key="q.id" :label="`第 ${q.question_order + 1} 题`">
            <el-input
              v-model="answers[q.id]"
              size="small"
              :placeholder="`${q.content.slice(0, 40)}…`"
            />
          </el-form-item>
        </div>
      </template>
      <el-form-item v-else label="作业文件">
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          :accept="form.content_type === 'image' ? 'image/png,image/jpeg,image/gif,image/webp' : 'application/pdf'"
          :on-change="onFileChange"
          :on-remove="() => (form.file = null)"
        >
          <el-icon style="font-size: 40px; color: #909399"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">上传后系统将自动识别并进入 AI 批改流程</div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>
    <div style="color: #909399; font-size: 12px">
      提交后将以此学生身份生成提交记录，经 OCR → AI 批改后可在「提交记录」与「教师复核」中处理。
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="onSubmit">提交作业</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { listStudents } from '../../api/classes'
import { teacherSubmitAssignment } from '../../api/submissions'

const props = defineProps({
  assignment: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['submitted'])

const visible = ref(false)
const students = ref([])
const submitting = ref(false)
const form = reactive({
  student_id: null,
  content_type: 'text',
  content_text: '',
  file: null,
})
const answers = reactive({})

const canSubmit = computed(() => {
  if (!form.student_id) return false
  if (form.content_type === 'text') return !!form.content_text.trim()
  return !!form.file
})

function open() {
  visible.value = true
  students.value = []
  Object.assign(form, { student_id: null, content_type: 'text', content_text: '', file: null })
  Object.keys(answers).forEach((k) => delete answers[k])
  loadStudents()
}

function onFileChange(uploadFile) {
  form.file = uploadFile.raw || null
}

async function loadStudents() {
  if (!props.assignment?.class_id) return
  try {
    students.value = await listStudents(props.assignment.class_id)
  } catch (e) {
    ElMessage.error('加载学生列表失败')
  }
}

watch(
  () => props.assignment?.questions,
  (qs) => {
    if (!qs) return
    qs.forEach((q) => {
      if (!(q.id in answers)) answers[q.id] = ''
    })
  },
  { immediate: true },
)

async function onSubmit() {
  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('student_id', form.student_id)
    formData.append('content_type', form.content_type)
    if (form.content_type === 'text') {
      formData.append('content_text', form.content_text)
      const answersJson = Object.entries(answers)
        .filter(([, v]) => v !== '')
        .map(([qid, v]) => ({ question_id: Number(qid), student_answer: v }))
      if (answersJson.length) {
        formData.append('answers_json', JSON.stringify(answersJson))
      }
    } else {
      formData.append('file', form.file)
    }
    await teacherSubmitAssignment(props.assignment.id, formData)
    ElMessage.success('提交成功，已进入批改流程')
    visible.value = false
    emit('submitted')
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>