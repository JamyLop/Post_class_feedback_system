<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <span class="page-title">{{ assignment.title }}</span>
      <div>
        <el-button @click="$router.push(`/teacher/assignments/${assignment.id}/submissions`)">提交记录</el-button>
        <el-button type="primary" plain @click="submitDialog.open()">代学生提交</el-button>
        <el-button type="primary" @click="dialogVisible = true">添加题目</el-button>
        <el-button
          v-if="assignment.status === 'draft'"
          type="success"
          :disabled="!(assignment.questions && assignment.questions.length)"
          @click="onPublish"
        >
          发布作业
        </el-button>
      </div>
    </div>

    <el-descriptions :column="4" border style="margin-bottom: 16px">
      <el-descriptions-item label="科目">{{ assignment.subject }}</el-descriptions-item>
      <el-descriptions-item label="班级ID">{{ assignment.class_id }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ statusLabel(assignment.status) }}</el-descriptions-item>
      <el-descriptions-item label="题目数">{{ assignment.questions?.length || 0 }}</el-descriptions-item>
      <el-descriptions-item label="描述">{{ assignment.description || '—' }}</el-descriptions-item>
      <el-descriptions-item label="截止时间">{{ assignment.due_at || '—' }}</el-descriptions-item>
    </el-descriptions>

    <el-timeline v-if="assignment.questions && assignment.questions.length">
      <el-timeline-item
        v-for="q in assignment.questions"
        :key="q.id"
        :timestamp="`${q.score} 分 · ${typeLabel(q.question_type)}`"
      >
        <div>{{ q.content }}</div>
        <div style="color: #909399; font-size: 13px; margin-top: 4px">
          标准答案：{{ q.standard_answer || '—' }}
        </div>
      </el-timeline-item>
    </el-timeline>
    <el-empty v-else description="还没有题目，点击右上角「添加题目」" />

    <el-dialog v-model="dialogVisible" title="从题库添加题目" width="640px">
      <el-table :data="questions" height="360" @selection-change="(rows) => (selected = rows)">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="question_type" label="题型" width="90" />
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
        <el-table-column prop="score" label="分数" width="80" />
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selected.length" @click="onAddQuestions">
          添加选中题目
        </el-button>
      </template>
    </el-dialog>

    <TeacherSubmitDialog ref="submitDialog" :assignment="assignment" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { addQuestions, getAssignment, publishAssignment } from '../../api/assignments'
import { listQuestions } from '../../api/questions'
import TeacherSubmitDialog from './TeacherSubmitDialog.vue'

const route = useRoute()
const assignment = ref({})
const questions = ref([])
const selected = ref([])
const dialogVisible = ref(false)
const loading = ref(false)
const submitDialog = ref()

const typeLabels = {
  single_choice: '单选', multiple_choice: '多选', judge: '判断',
  fill: '填空', calculation: '计算', short_answer: '简答',
}
const typeLabel = (t) => typeLabels[t] || t
const statusLabel = (s) => ({ draft: '草稿', published: '已发布', closed: '已关闭', archived: '已归档' }[s] || s)

async function load() {
  loading.value = true
  try {
    assignment.value = await getAssignment(route.params.id)
  } finally {
    loading.value = false
  }
}

async function onAddQuestions() {
  await addQuestions(assignment.value.id, selected.value.map((q) => q.id))
  ElMessage.success('已添加')
  dialogVisible.value = false
  load()
}

async function onPublish() {
  await publishAssignment(assignment.value.id)
  ElMessage.success('已发布，学生可见')
  load()
}

onMounted(async () => {
  await load()
  questions.value = await listQuestions()
})
</script>
