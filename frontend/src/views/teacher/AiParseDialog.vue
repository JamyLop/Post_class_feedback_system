<template>
  <el-dialog v-model="visible" title="AI 解析题目" width="860px" top="6vh">
    <el-steps :active="step" finish-status="success" simple style="margin-bottom: 20px">
      <el-step title="输入题目" />
      <el-step title="解析预览" />
      <el-step title="入库" />
    </el-steps>

    <!-- 第 1 步：输入 -->
    <div v-show="step === 1">
      <el-tabs v-model="inputMode">
        <el-tab-pane label="图片上传" name="image">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept="image/png,image/jpeg,image/gif,image/webp"
            :on-change="onImageChange"
            :on-remove="() => (imageFile = null)"
          >
            <el-icon style="font-size: 40px; color: #909399"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽题目图片到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持题目截图/拍照，AI 将识别图片中的全部文字并解析为题</div>
            </template>
          </el-upload>
        </el-tab-pane>
        <el-tab-pane label="文字粘贴" name="text">
          <el-input
            v-model="textContent"
            type="textarea"
            :rows="8"
            placeholder="粘贴题目文字，多道题用空行分隔，例如：&#10;&#10;1. 解方程 x²-4=0&#10;&#10;2. 计算 3+5"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 第 2 步：预览 -->
    <div v-show="step === 2">
      <div style="margin-bottom: 12px; color: #606266; font-size: 13px">
        已解析 <b>{{ parsed.length }}</b> 道题，可编辑内容后勾选入库：
      </div>
      <el-table :data="parsed" border max-height="420" @selection-change="(rows) => (selected = rows)">
        <el-table-column type="selection" width="46" />
        <el-table-column label="题型" width="110">
          <template #default="{ row }">
            <el-select v-model="row.question_type" size="small">
              <el-option v-for="(v, k) in typeLabels" :key="k" :label="v" :value="k" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="题干">
          <template #default="{ row }">
            <el-input v-model="row.content" size="small" type="textarea" :rows="2" />
          </template>
        </el-table-column>
        <el-table-column label="标准答案" width="180">
          <template #default="{ row }">
            <el-input v-model="row.standard_answer" size="small" type="textarea" :rows="2" />
          </template>
        </el-table-column>
        <el-table-column label="分值" width="90">
          <template #default="{ row }">
            <el-input-number v-model="row.score" size="small" :min="0" :step="1" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="难度" width="90">
          <template #default="{ row }">
            <el-input-number v-model="row.difficulty" size="small" :min="0" :max="1" :step="0.1" style="width: 100%" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 第 3 步：完成 -->
    <div v-show="step === 3" style="text-align: center; padding: 24px 0">
      <el-result icon="success" :title="`已入库 ${createdCount} 道题目`" />
    </div>

    <template #footer>
      <el-button @click="onCancel">{{ step === 3 ? '关闭' : '取消' }}</el-button>
      <el-button v-if="step === 1" type="primary" :loading="parsing" @click="onParse">开始解析</el-button>
      <el-button v-if="step === 2" :disabled="!selected.length" type="primary" :loading="saving" @click="onSave">
        入库选中（{{ selected.length }}）
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { batchCreateQuestions, parseQuestions } from '../../api/questions'

const emit = defineEmits(['created'])

const visible = ref(false)
const step = ref(1)
const inputMode = ref('image')
const imageFile = ref(null)
const textContent = ref('')
const parsed = ref([])
const selected = ref([])
const parsing = ref(false)
const saving = ref(false)
const createdCount = ref(0)

const typeLabels = {
  single_choice: '单选', multiple_choice: '多选', judge: '判断',
  fill: '填空', calculation: '计算', short_answer: '简答',
}

const hasInput = computed(() =>
  inputMode.value === 'image' ? !!imageFile.value : !!textContent.value.trim(),
)

function open() {
  step.value = 1
  parsed.value = []
  selected.value = []
  imageFile.value = null
  textContent.value = ''
  createdCount.value = 0
  visible.value = true
}

function onImageChange(uploadFile) {
  imageFile.value = uploadFile.raw || null
}

function onCancel() {
  if (step.value === 3) {
    emit('created')
    visible.value = false
    return
  }
  visible.value = false
}

async function onParse() {
  if (!hasInput.value) {
    ElMessage.warning(inputMode.value === 'image' ? '请先选择题目图片' : '请粘贴题目文字')
    return
  }
  const formData = new FormData()
  if (inputMode.value === 'image') {
    formData.append('file', imageFile.value)
  } else {
    formData.append('content_text', textContent.value)
  }
  parsing.value = true
  try {
    parsed.value = await parseQuestions(formData)
    step.value = 2
  } finally {
    parsing.value = false
  }
}

async function onSave() {
  if (!selected.value.length) {
    ElMessage.warning('请至少勾选一道题')
    return
  }
  saving.value = true
  try {
    const questions = selected.value.map((q) => ({
      subject: '数学',
      grade: '初中',
      question_type: q.question_type,
      content: q.content,
      standard_answer: q.standard_answer || '',
      score: q.score || 0,
      difficulty: q.difficulty ?? 0.5,
      knowledge_points: [],
    }))
    const created = await batchCreateQuestions(questions)
    createdCount.value = created.length
    step.value = 3
    ElMessage.success(`已入库 ${created.length} 道题目`)
  } finally {
    saving.value = false
  }
}

defineExpose({ open })
</script>