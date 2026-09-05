<template>
  <div class="page feedback-manage-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">课后学情反馈与周报</h1>
        <p class="header-desc">AI 自动生成单次作业针对性评语或周期学情周报，支持教师编辑与定稿发布。</p>
      </div>
      <el-button :disabled="!studentId" @click="load">
        <el-icon><Refresh /></el-icon>刷新列表
      </el-button>
    </div>

    <el-card shadow="never" style="margin-bottom: 16px">
      <el-form inline>
        <el-form-item label="班级">
          <el-select v-model="classId" style="width: 180px" @change="onClassChange">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生">
          <el-select v-model="studentId" style="width: 180px" @change="load">
            <el-option v-for="item in students" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="reportType">
            <el-radio-button value="assignment">单次作业</el-radio-button>
            <el-radio-button value="weekly">学生周报</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="reportType === 'assignment'" label="作业">
          <el-select v-model="assignmentId" style="width: 220px">
            <el-option v-for="item in classAssignments" :key="item.id" :label="item.title" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="generating" :disabled="!canGenerate" @click="generate">
            生成反馈
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-empty v-if="studentId && !reports.length" description="暂无反馈，可先生成" />
    <el-empty v-else-if="!studentId" description="请先选择班级和学生" />
    <el-card v-for="report in reports" :key="report.id" shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div class="report-header">
          <span>{{ report.report_type === 'weekly' ? '学生周报' : `作业反馈 #${report.assignment_id}` }}</span>
          <el-tag :type="statusType(report.status)">{{ statusText(report.status) }}</el-tag>
        </div>
      </template>
      <el-alert v-if="report.error_message" type="error" :closable="false" :title="report.error_message" />
      <el-input
        v-model="report.final_content"
        type="textarea"
        :rows="6"
        maxlength="2000"
        show-word-limit
        :disabled="!['generated', 'published'].includes(report.status)"
      />
      <div class="actions">
        <span class="meta">模型：{{ report.model_name || '-' }} · 耗时：{{ report.duration_ms }}ms · Token：{{ report.total_tokens }}</span>
        <el-button v-if="['generated', 'published'].includes(report.status)" @click="save(report)">保存修改</el-button>
        <el-button v-if="report.status === 'generated'" type="primary" @click="publish(report)">发布给学生</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listAssignments } from '../../api/assignments'
import { listClasses, listStudents } from '../../api/classes'
import { generateFeedback, listFeedback, publishFeedback, updateFeedback } from '../../api/feedback'

const classes = ref([])
const students = ref([])
const assignments = ref([])
const reports = ref([])
const classId = ref(null)
const studentId = ref(null)
const assignmentId = ref(null)
const reportType = ref('assignment')
const generating = ref(false)

const classAssignments = computed(() => assignments.value.filter((item) => item.class_id === classId.value))
const canGenerate = computed(() => studentId.value && classId.value && (reportType.value === 'weekly' || assignmentId.value))
const statusText = (status) => ({ generating: '生成中', generated: '待发布', published: '已发布', failed: '生成失败' }[status] || status)
const statusType = (status) => ({ generated: 'warning', published: 'success', failed: 'danger' }[status] || 'info')

async function onClassChange() {
  studentId.value = null
  assignmentId.value = null
  reports.value = []
  students.value = classId.value ? await listStudents(classId.value) : []
}

async function load() {
  if (!studentId.value) return
  reports.value = await listFeedback(studentId.value, { class_id: classId.value })
}

async function generate() {
  generating.value = true
  try {
    await generateFeedback(studentId.value, {
      report_type: reportType.value,
      class_id: classId.value,
      assignment_id: reportType.value === 'assignment' ? assignmentId.value : null,
    })
    ElMessage.success('反馈生成任务已启动')
    await load()
  } finally {
    generating.value = false
  }
}

async function save(report) {
  await updateFeedback(report.id, { final_content: report.final_content })
  ElMessage.success('反馈已保存')
  await load()
}

async function publish(report) {
  await updateFeedback(report.id, { final_content: report.final_content })
  await publishFeedback(report.id)
  ElMessage.success('反馈已发布')
  await load()
}

onMounted(async () => {
  ;[classes.value, assignments.value] = await Promise.all([listClasses(), listAssignments()])
})
</script>

<style scoped>
.feedback-manage-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.header-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
}

.report-header, .actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.actions {
  margin-top: 14px;
  justify-content: flex-end;
}

.meta {
  margin-right: auto;
  color: #94a3b8;
  font-size: 12px;
  font-family: monospace;
}
</style>
