<template>
  <section class="page case-page">
    <el-skeleton v-if="loading" :rows="9" animated class="page-skeleton" />

    <template v-else-if="detail">
      <button class="back-link" type="button" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon><span>{{ auth.role === 'parent' ? '返回孩子档案' : '返回学生档案' }}</span>
      </button>

      <header class="case-header">
        <div class="case-heading">
          <div class="title-line">
            <h1>{{ detail.student_name || `学生 #${detail.student_id}` }}</h1>
            <span class="title-suffix">学业发展总案</span>
          </div>
          <div class="case-meta">
            <span class="status-badge" :class="`is-${detail.status}`"><span class="status-dot"></span>{{ labels[detail.status] || detail.status }}</span>
            <span>{{ detail.class_name || `班级 #${detail.class_id}` }}</span>
            <span>第 {{ detail.version }} 版</span>
            <span>更新于 {{ formatDate(detail.updated_at) }}</span>
          </div>
        </div>
        <div class="case-actions">
          <el-tooltip content="导出功能将在打印模板验收后开放" placement="bottom">
            <span><el-button disabled><el-icon><Document /></el-icon>导出 DOCX</el-button></span>
          </el-tooltip>
          <el-button v-if="detail.status === 'draft'" type="primary" :loading="submitting" @click="submitForConfirmation">提交教师确认</el-button>
        </div>
      </header>

      <div class="state-banner" :class="`is-${detail.status}`">
        <el-icon class="state-icon"><WarningFilled v-if="detail.status === 'draft'" /><CircleCheckFilled v-else /></el-icon>
        <div><strong>{{ stateTitle }}</strong><p>{{ stateDescription }}</p></div>
      </div>

      <el-tabs v-model="active" class="case-tabs">
        <el-tab-pane label="总览" name="overview">
          <div class="overview-layout">
            <main class="reading-column">
              <article class="content-section">
                <div class="section-heading"><div><span class="section-marker"></span><h2>总体问题</h2></div><span>历史材料诊断摘要</span></div>
                <div v-if="problemSections.length" class="insight-list">
                  <div v-for="item in problemSections" :key="`${item.label}-${item.text}`" class="insight-row"><span class="subject-label">{{ item.label }}</span><p>{{ item.text }}</p></div>
                </div>
                <p v-else class="placeholder-copy">尚未填写总体问题。</p>
              </article>

              <article class="content-section">
                <div class="section-heading"><div><span class="section-marker"></span><h2>升学目标</h2></div><span>分阶段目标</span></div>
                <div v-if="targetSections.length" class="target-list">
                  <div v-for="item in targetSections" :key="`${item.label}-${item.text}`" class="target-row"><span>{{ item.label }}</span><p>{{ item.text }}</p></div>
                </div>
                <p v-else class="placeholder-copy">尚未填写升学目标。</p>
              </article>
            </main>

            <aside class="case-rail">
              <section class="rail-section"><span class="rail-label">当前状态</span><strong>{{ labels[detail.status] || detail.status }}</strong><p>{{ detail.current_summary || '尚未填写状态说明' }}</p></section>
              <section class="rail-section compact">
                <div><span>学科方案</span><strong>{{ detail.subject_plans.length }}</strong></div>
                <div><span>阶段目标</span><strong>{{ detail.goals.length }}</strong></div>
                <div><span>执行任务</span><strong>{{ detail.tasks.length }}</strong></div>
                <div><span>督查记录</span><strong>{{ detail.reviews.length }}</strong></div>
              </section>
              <section v-if="auth.role !== 'parent'" class="rail-section source-note"><span class="rail-label">数据来源</span><p>历史 DOCX 试导入</p><small>解析内容尚未成为正式方案，需由班主任核对后提交确认。</small></section>
              <section v-if="detail.status === 'draft'" class="rail-section next-steps">
                <span class="rail-label">确认前检查</span>
                <ol><li><span>1</span>核对诊断与成绩信息</li><li><span>2</span>确认学科方案负责人</li><li><span>3</span>补充可执行目标与任务</li></ol>
              </section>
            </aside>
          </div>
        </el-tab-pane>

        <el-tab-pane label="学科方案" name="subjects">
          <div v-if="subjectOptions.length" class="subject-workspace">
            <nav class="subject-nav" aria-label="选择学科">
              <div class="subject-nav-heading"><strong>全部科目</strong><span>{{ subjectOptions.length }} 科</span></div>
              <button
                v-for="subject in subjectOptions"
                :key="subject"
                class="subject-nav-item"
                :class="{ 'is-active': selectedSubject === subject }"
                type="button"
                :disabled="(editingPlan || editingTask) && selectedSubject !== subject"
                :aria-current="selectedSubject === subject ? 'page' : undefined"
                @click="selectSubject(subject)"
              >
                <span class="subject-avatar">{{ subject.slice(0, 1) }}</span>
                <span><strong>{{ subject }}</strong><small>{{ subjectStatusText(subject) }}</small></span>
                <span class="subject-task-count">{{ tasksFor(subject).length }}</span>
                <el-icon><ArrowRight /></el-icon>
              </button>
              <el-dropdown v-if="availableSubjects.length" class="subject-add" trigger="click" :disabled="editingPlan || editingTask" @command="addSubject">
                <el-button link type="primary"><el-icon><Plus /></el-icon>添加学科</el-button>
                <template #dropdown><el-dropdown-menu><el-dropdown-item v-for="subject in availableSubjects" :key="subject" :command="subject">{{ subject }}</el-dropdown-item></el-dropdown-menu></template>
              </el-dropdown>
            </nav>

            <main class="subject-detail">
              <header class="subject-detail-header">
                <div><span class="subject-chip">{{ selectedSubject }}</span><h2>{{ selectedSubject }}学业提升方案</h2></div>
                <div class="subject-header-actions">
                  <div class="subject-counts"><span>{{ tasksFor(selectedSubject).length }} 项任务</span><span>{{ checkinsFor(selectedSubject).length }} 条执行记录</span></div>
                  <el-button v-if="canEditPlan && !editingPlan && !editingTask" plain @click="startPlanEdit"><el-icon><EditPen /></el-icon>编辑方案</el-button>
                  <template v-else-if="editingPlan">
                    <el-button :disabled="savingPlan" @click="cancelPlanEdit">取消编辑</el-button>
                    <el-button type="primary" :loading="savingPlan" @click="savePlan">保存方案</el-button>
                  </template>
                </div>
              </header>

              <div v-if="editingPlan" class="editing-note"><el-icon><EditPen /></el-icon><span>正在编辑 {{ selectedSubject }}方案，所有字段将按原文完整保存。</span></div>

              <section class="subject-section">
                <div class="subject-section-heading"><div><el-icon><Search /></el-icon><h3>问题</h3></div><span>明确当前差距与主要原因</span></div>
                <el-form v-if="editingPlan" label-position="top" class="subject-edit-form">
                  <el-form-item label="问题定位"><el-input v-model="planForm.problem_location" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" placeholder="完整填写该学科的问题定位" /></el-form-item>
                  <el-form-item label="原因剖析"><el-input v-model="planForm.cause_analysis" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" placeholder="完整填写问题产生的原因" /></el-form-item>
                </el-form>
                <dl v-else class="subject-fields">
                  <div><dt>问题定位</dt><dd>{{ (selectedPlan?.problem_location || subjectProblemText) || '该学科尚未完成问题定位。' }}</dd></div>
                  <div><dt>原因剖析</dt><dd>{{ (selectedPlan?.cause_analysis || '') || '尚未补充原因分析，需由对应学科教师确认。' }}</dd></div>
                </dl>
              </section>

              <section class="subject-section">
                <div class="subject-section-heading"><div><el-icon><Calendar /></el-icon><h3>计划</h3></div><span>目标要求与具体行动安排</span></div>
                <el-form v-if="editingPlan" label-position="top" class="subject-edit-form plan-edit-form">
                  <el-form-item label="奋斗目标"><el-input v-model="planForm.struggle_goal" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" placeholder="完整填写短期、中期和高考目标" /></el-form-item>
                  <el-form-item label="高考要求"><el-input v-model="planForm.gaokao_requirement" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" placeholder="完整填写该学科的高考要求" /></el-form-item>
                  <el-form-item label="具体强化"><el-input v-model="planForm.reinforcement" type="textarea" :autosize="{ minRows: 3, maxRows: 14 }" placeholder="完整填写具体强化措施" /></el-form-item>
                </el-form>
                <dl v-else class="subject-fields plan-fields">
                  <div><dt>奋斗目标</dt><dd>{{ (selectedPlan?.struggle_goal || subjectTargetText) || '尚未建立该学科奋斗目标。' }}</dd></div>
                  <div><dt>高考要求</dt><dd>{{ (selectedPlan?.gaokao_requirement || '') || '尚未补充高考要求。' }}</dd></div>
                  <div><dt>具体强化</dt><dd>{{ (selectedPlan?.reinforcement || '') || '尚未制定具体强化方案。' }}</dd></div>
                </dl>
                <div class="task-list-heading">
                  <div><strong>任务安排</strong><span>{{ tasksFor(selectedSubject).length }} 项</span></div>
                  <el-button v-if="canEditTasks && !editingTask" link type="primary" @click="startTaskEdit()"><el-icon><Plus /></el-icon>新增任务</el-button>
                </div>
                <el-form v-if="editingTask" label-position="top" class="task-edit-form">
                  <el-form-item label="任务名称"><el-input v-model="taskForm.title" placeholder="填写完整任务名称" /></el-form-item>
                  <el-form-item label="任务内容"><el-input v-model="taskForm.description" type="textarea" :autosize="{ minRows: 4, maxRows: 16 }" placeholder="填写完整任务内容和执行要求" /></el-form-item>
                  <div class="task-form-grid">
                    <el-form-item label="任务周期"><el-select v-model="taskForm.cadence"><el-option label="日计划" value="daily" /><el-option label="周计划" value="weekly" /><el-option label="月计划" value="monthly" /></el-select></el-form-item>
                    <el-form-item label="开始日期"><el-date-picker v-model="taskForm.starts_on" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" /></el-form-item>
                    <el-form-item label="截止日期"><el-date-picker v-model="taskForm.due_on" type="date" value-format="YYYY-MM-DD" placeholder="选择截止日期" /></el-form-item>
                  </div>
                  <div class="task-form-actions"><el-button :disabled="savingTask" @click="cancelTaskEdit">取消</el-button><el-button type="primary" :loading="savingTask" @click="saveTask">保存任务</el-button></div>
                </el-form>
                <div v-if="tasksFor(selectedSubject).length" class="task-list">
                  <article v-for="task in tasksFor(selectedSubject)" :key="task.id" class="task-row">
                    <div><strong>{{ task.title }}</strong><p>{{ task.description || '暂无补充说明' }}</p></div>
                    <div class="task-side"><div class="task-meta"><span>{{ cadenceLabel(task.cadence) }}</span><span>{{ formatShortDate(task.starts_on) }} 至 {{ formatShortDate(task.due_on) }}</span><span>{{ taskStatusLabel(task.status) }}</span></div><el-button v-if="canEditTasks && !editingTask" link @click="startTaskEdit(task)">编辑任务</el-button></div>
                  </article>
                </div>
                <div v-else class="inline-empty"><p>该学科尚未安排日、周或月任务。</p></div>
              </section>

              <section class="subject-section">
                <div class="subject-section-heading"><div><el-icon><CircleCheck /></el-icon><h3>执行记录</h3></div><span>班主任核实并记录任务完成情况</span></div>
                <el-form v-if="detail.can_manage && tasksFor(selectedSubject).length" label-position="top" class="checkin-form">
                  <div class="checkin-form-grid">
                    <el-form-item label="对应任务"><el-select v-model="checkinForm.task_id" placeholder="选择要记录的任务"><el-option v-for="task in tasksFor(selectedSubject)" :key="task.id" :label="task.title" :value="task.id" /></el-select></el-form-item>
                    <el-form-item label="完成度"><el-input-number v-model="checkinForm.completion_rate" :min="0" :max="100" :step="10" /><span class="percent-suffix">%</span></el-form-item>
                  </div>
                  <el-form-item label="班主任记录"><el-input v-model="checkinForm.self_check" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="完整记录学生实际执行情况、发现的问题和后续要求" /></el-form-item>
                  <div class="task-form-actions"><el-button type="primary" :loading="savingCheckin" @click="saveCheckin">保存执行记录</el-button></div>
                </el-form>
                <div v-if="checkinsFor(selectedSubject).length" class="checkin-list">
                  <article v-for="checkin in checkinsFor(selectedSubject)" :key="checkin.id" class="checkin-row">
                    <div class="completion-rate"><strong>{{ checkin.completion_rate }}%</strong><span>完成度</span></div>
                    <div><strong>{{ taskTitle(checkin.task_id) }}</strong><p>{{ checkin.self_check || '班主任未填写补充说明' }}</p><time>{{ formatDateTime(checkin.checked_in_at) }}</time></div>
                  </article>
                </div>
                <div v-else class="inline-empty"><p>该学科尚无执行记录，班主任核实任务执行情况后在此登记。</p></div>
              </section>
            </main>
          </div>
          <div v-else class="empty-panel subject-empty"><h3>尚未建立学科方案</h3><p>班主任可以直接选择学科，从空白方案开始完整填写。</p><div class="subject-create-actions"><el-button v-for="subject in subjectOrder" :key="subject" type="primary" plain @click="addSubject(subject)">新建{{ subject }}方案</el-button></div></div>
        </el-tab-pane>
        <el-tab-pane label="督查复盘" name="reviews"><el-timeline v-if="detail.reviews.length" class="review-timeline"><el-timeline-item v-for="review in detail.reviews" :key="review.id" :timestamp="review.reviewed_at"><b>{{ review.review_level }}</b><p>{{ review.problem }}</p><small>{{ review.corrective_action }}</small></el-timeline-item></el-timeline><div v-else class="empty-panel"><h3>暂无督查记录</h3><p>方案进入执行阶段后，班主任记录过程，管理员提交校级督查。</p></div></el-tab-pane>
        <el-tab-pane label="历史版本" name="versions"><div class="empty-panel"><h3>当前为第 {{ detail.version }} 版</h3><p>正式调整后，旧版本将在这里保留并支持对比。</p></div></el-tab-pane>
      </el-tabs>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Calendar, CircleCheck, CircleCheckFilled, Document, EditPen, Plus, Search, WarningFilled } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import { checkinCaseTask, createCaseTask, getStudentCase, transitionStudentCase, updateCaseTask, upsertSubjectPlan } from '../../api/studentCases'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const editingPlan = ref(false)
const savingPlan = ref(false)
const editingTask = ref(null)
const savingTask = ref(false)
const savingCheckin = ref(false)
const detail = ref(null)
const active = ref('overview')
const selectedSubject = ref('')
const manualSubjects = ref([])
const planForm = ref(createEmptyPlanForm())
const taskForm = ref(createEmptyTaskForm())
const checkinForm = ref({ task_id: null, completion_rate: 0, self_check: '' })
const labels = { draft: '草稿', pending_confirmation: '待确认', executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }
const subjectOrder = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
const stateTitle = computed(() => detail.value?.status === 'draft' ? '历史材料已导入，等待教师核对' : `方案当前处于${labels[detail.value?.status] || '处理中'}状态`)
const stateDescription = computed(() => detail.value?.status === 'draft' ? '请由班主任确认诊断、目标和学科方案内容。进入执行后，关联家长才能查看正式方案。' : '所有后续调整都会保留历史版本，家长始终看到有版本依据的正式内容。')

function splitStructuredText(value, fallbackLabel) {
  if (!value) return []
  return value.split(/[；;]/).map((part) => part.trim()).filter(Boolean).flatMap((part) => {
    const match = part.match(/^([^：:]{1,14})[：:]\s*(.+)$/)
    if (!match) return [{ label: fallbackLabel, text: part }]
    const rawLabel = match[1].trim().replace(/^\d+[.、]\s*/, '')
    const labels = rawLabel.split(/[\/／]/).map((label) => label.trim()).filter(Boolean)
    // 历史文档可能把多门学科写在同一项中；展示时拆开标签，但完整保留共同的原始描述。
    return labels.map((label) => ({ label, text: match[2].trim() }))
  })
}

const problemSections = computed(() => splitStructuredText(detail.value?.overall_problem, '综合'))
const targetSections = computed(() => splitStructuredText(detail.value?.admission_target, '总体目标'))
const subjectOptions = computed(() => {
  const found = new Set()
  problemSections.value.forEach((item) => { if (subjectOrder.includes(item.label)) found.add(item.label) })
  detail.value?.subject_plans?.forEach((item) => { if (item.subject) found.add(item.subject) })
  detail.value?.goals?.forEach((item) => { if (item.subject) found.add(item.subject) })
  detail.value?.tasks?.forEach((item) => { if (item.subject) found.add(item.subject) })
  manualSubjects.value.forEach((item) => found.add(item))
  return [...found].sort((a, b) => {
    const aIndex = subjectOrder.indexOf(a)
    const bIndex = subjectOrder.indexOf(b)
    if (aIndex === -1 || bIndex === -1) return a.localeCompare(b, 'zh-CN')
    return aIndex - bIndex
  })
})
const selectedPlan = computed(() => detail.value?.subject_plans?.find((item) => item.subject === selectedSubject.value))
const availableSubjects = computed(() => subjectOrder.filter((item) => !subjectOptions.value.includes(item)))
const canEditPlan = computed(() => detail.value?.can_manage && ['draft', 'pending_confirmation', 'adjusted'].includes(detail.value?.status))
const canEditTasks = computed(() => detail.value?.can_manage && detail.value?.status !== 'archived' && !editingPlan.value)
// 学科方案缺失时展示总案原文作为参考，不抽取、不概括，避免导入内容被压缩。
const subjectProblemText = computed(() => detail.value?.overall_problem || '')
const subjectTargetText = computed(() => detail.value?.admission_target || '')

function createEmptyPlanForm() {
  return { problem_location: '', cause_analysis: '', struggle_goal: '', gaokao_requirement: '', reinforcement: '' }
}

function createEmptyTaskForm() {
  const today = new Date().toISOString().slice(0, 10)
  return { title: '', description: '', cadence: 'daily', starts_on: today, due_on: today }
}

function selectSubject(subject) {
  if ((editingPlan.value || editingTask.value) && subject !== selectedSubject.value) return
  selectedSubject.value = subject
  checkinForm.value.task_id = tasksFor(subject)[0]?.id || null
}

function addSubject(subject) {
  if (!manualSubjects.value.includes(subject)) manualSubjects.value.push(subject)
  selectedSubject.value = subject
  startPlanEdit()
}

function startPlanEdit() {
  const plan = selectedPlan.value
  planForm.value = plan ? {
    problem_location: plan.problem_location || '',
    cause_analysis: plan.cause_analysis || '',
    struggle_goal: plan.struggle_goal || '',
    gaokao_requirement: plan.gaokao_requirement || '',
    reinforcement: plan.reinforcement || '',
  } : createEmptyPlanForm()
  editingPlan.value = true
}

function cancelPlanEdit() {
  editingPlan.value = false
  planForm.value = createEmptyPlanForm()
}

async function savePlan() {
  if (!detail.value || !selectedSubject.value) return
  const teacherId = selectedPlan.value?.teacher_id || auth.user?.id
  if (!teacherId) {
    ElMessage.error('无法识别当前教师，请重新登录后再保存')
    return
  }
  savingPlan.value = true
  try {
    const saved = await upsertSubjectPlan(detail.value.id, selectedSubject.value, {
      subject: selectedSubject.value,
      teacher_id: teacherId,
      ...planForm.value,
    })
    const index = detail.value.subject_plans.findIndex((item) => item.subject === selectedSubject.value)
    if (index >= 0) detail.value.subject_plans.splice(index, 1, saved)
    else detail.value.subject_plans.push(saved)
    editingPlan.value = false
    planForm.value = createEmptyPlanForm()
    ElMessage.success(`${selectedSubject.value}方案已保存`)
  } finally {
    savingPlan.value = false
  }
}

function startTaskEdit(task = null) {
  editingTask.value = task?.id || 'new'
  taskForm.value = task ? {
    title: task.title || '',
    description: task.description || '',
    cadence: task.cadence || 'daily',
    starts_on: task.starts_on || '',
    due_on: task.due_on || '',
  } : createEmptyTaskForm()
}

function cancelTaskEdit() {
  editingTask.value = null
  taskForm.value = createEmptyTaskForm()
}

async function saveTask() {
  if (!taskForm.value.title.trim()) {
    ElMessage.warning('请填写任务名称')
    return
  }
  if (!taskForm.value.starts_on || !taskForm.value.due_on) {
    ElMessage.warning('请选择任务开始和截止日期')
    return
  }
  if (taskForm.value.due_on < taskForm.value.starts_on) {
    ElMessage.warning('截止日期不能早于开始日期')
    return
  }
  savingTask.value = true
  try {
    const payload = { subject: selectedSubject.value, ...taskForm.value, title: taskForm.value.title.trim() }
    const saved = editingTask.value === 'new'
      ? await createCaseTask(detail.value.id, payload)
      : await updateCaseTask(detail.value.id, editingTask.value, payload)
    const index = detail.value.tasks.findIndex((item) => item.id === saved.id)
    if (index >= 0) detail.value.tasks.splice(index, 1, saved)
    else detail.value.tasks.push(saved)
    cancelTaskEdit()
    ElMessage.success('任务已保存')
  } finally {
    savingTask.value = false
  }
}

function tasksFor(subject) {
  return detail.value?.tasks?.filter((item) => item.subject === subject) || []
}

function checkinsFor(subject) {
  const taskIds = new Set(tasksFor(subject).map((item) => item.id))
  return detail.value?.task_checkins?.filter((item) => taskIds.has(item.task_id)) || []
}

async function saveCheckin() {
  if (!checkinForm.value.task_id) {
    ElMessage.warning('请选择对应任务')
    return
  }
  savingCheckin.value = true
  try {
    const saved = await checkinCaseTask(checkinForm.value.task_id, {
      completion_rate: checkinForm.value.completion_rate,
      self_check: checkinForm.value.self_check,
    })
    detail.value.task_checkins.unshift(saved)
    const task = detail.value.tasks.find((item) => item.id === saved.task_id)
    if (task) task.status = saved.completion_rate === 100 ? 'completed' : saved.completion_rate > 0 ? 'in_progress' : 'pending'
    checkinForm.value = { task_id: null, completion_rate: 0, self_check: '' }
    ElMessage.success('执行记录已保存')
  } finally {
    savingCheckin.value = false
  }
}

function subjectStatusText(subject) {
  if (detail.value?.subject_plans?.some((item) => item.subject === subject)) return '方案已录入'
  if (tasksFor(subject).length) return '已有任务'
  return '待完善'
}

function taskTitle(taskId) {
  return detail.value?.tasks?.find((item) => item.id === taskId)?.title || '任务记录'
}

function cadenceLabel(value) {
  return { daily: '日计划', weekly: '周计划', monthly: '月计划' }[value] || value
}

function taskStatusLabel(value) {
  return { pending: '待执行', in_progress: '执行中', completed: '已完成', overdue: '已逾期' }[value] || value
}

function formatShortDate(value) {
  return value ? value.slice(5).replace('-', '/') : '未定'
}

function formatDate(value) {
  if (!value) return '暂无记录'
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}
function formatDateTime(value) {
  if (!value) return '暂无时间'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}
async function load() {
  loading.value = true
  try {
    detail.value = await getStudentCase(route.params.id)
    if (!subjectOptions.value.includes(selectedSubject.value)) selectedSubject.value = subjectOptions.value[0] || ''
    const firstTask = tasksFor(selectedSubject.value)[0]
    checkinForm.value.task_id = firstTask?.id || null
  } finally {
    loading.value = false
  }
}
async function submitForConfirmation() {
  await ElMessageBox.confirm('提交后总案将进入待确认状态，是否继续？', '提交教师确认', { confirmButtonText: '提交确认', cancelButtonText: '继续检查', type: 'warning' })
  submitting.value = true
  try { await transitionStudentCase(detail.value.id, { target_status: 'pending_confirmation', reason: '历史材料核对完成' }); ElMessage.success('已提交确认'); await load() } finally { submitting.value = false }
}
onMounted(load)
</script>

<style scoped>
.case-page { min-height: 100%; }.page-skeleton { padding-top: 42px; }
.back-link { display: inline-flex; align-items: center; gap: 6px; margin: 2px 0 20px; padding: 0; color: var(--ink-secondary); background: transparent; border: 0; cursor: pointer; font: inherit; }.back-link:hover { color: var(--brand); }
.case-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 28px; }.title-line { display: flex; align-items: baseline; gap: 12px; }.title-line h1 { margin: 0; color: var(--ink); font-size: 32px; line-height: 1.2; letter-spacing: -.025em; text-wrap: balance; }.title-suffix { color: var(--ink-secondary); font-size: 17px; font-weight: 500; }
.case-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; margin-top: 12px; color: var(--ink-muted); font-size: 13px; }.status-badge { display: inline-flex; align-items: center; gap: 7px; padding: 5px 9px; color: #8a5611; background: var(--warning-soft); border-radius: 999px; font-weight: 650; }.status-badge.is-executing, .status-badge.is-adjusted, .status-badge.is-archived { color: #23764a; background: oklch(0.95 0.035 155); }.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.case-actions { display: flex; gap: 10px; flex-shrink: 0; }.case-actions :deep(.el-button) { min-height: 38px; }
.state-banner { display: flex; align-items: flex-start; gap: 12px; margin: 26px 0 0; padding: 15px 18px; color: #774b14; background: var(--warning-soft); border-radius: var(--radius-md); }.state-banner:not(.is-draft) { color: #236747; background: oklch(0.96 0.025 155); }.state-icon { margin-top: 2px; font-size: 18px; }.state-banner strong { font-size: 14px; }.state-banner p { margin: 4px 0 0; max-width: 86ch; color: color-mix(in oklch, currentColor 78%, var(--ink)); font-size: 13px; line-height: 1.55; }
.case-tabs { margin-top: 20px; }.case-tabs :deep(.el-tabs__header) { position: sticky; top: 0; z-index: 5; margin: 0; background: var(--app-bg); }.case-tabs :deep(.el-tabs__nav-wrap::after) { height: 1px; background: var(--line); }.case-tabs :deep(.el-tabs__item) { height: 50px; padding: 0 22px; color: var(--ink-secondary); font-size: 14px; }.case-tabs :deep(.el-tabs__item.is-active) { color: var(--brand-strong); font-weight: 650; }.case-tabs :deep(.el-tabs__active-bar) { height: 3px; border-radius: 3px 3px 0 0; }.case-tabs :deep(.el-tabs__content) { overflow: visible; padding-top: 24px; }
.overview-layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 28px; align-items: start; }.reading-column { min-width: 0; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }.content-section { padding: 28px 30px 30px; }.content-section + .content-section { border-top: 1px solid var(--line); }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 22px; }.section-heading > div { display: flex; align-items: center; gap: 10px; }.section-heading h2 { margin: 0; font-size: 18px; letter-spacing: -.015em; }.section-heading > span { color: var(--ink-muted); font-size: 12px; }.section-marker { width: 9px; height: 9px; border-radius: 3px; background: var(--brand); }
.insight-row { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 14px; padding: 14px 0; border-bottom: 1px solid color-mix(in oklch, var(--line) 78%, transparent); }.insight-row:last-child, .target-row:last-child { border-bottom: 0; }.subject-label { align-self: start; justify-self: start; padding: 4px 8px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 6px; font-size: 12px; font-weight: 650; }.insight-row p, .target-row p { margin: 0; max-width: 76ch; color: var(--ink-secondary); font-size: 15px; line-height: 1.85; text-wrap: pretty; }
.target-row { display: grid; grid-template-columns: 118px minmax(0, 1fr); gap: 16px; padding: 15px 0; border-bottom: 1px solid color-mix(in oklch, var(--line) 78%, transparent); }.target-row > span { color: var(--ink); font-size: 14px; font-weight: 700; }.placeholder-copy { color: var(--ink-muted); }
.case-rail { overflow: hidden; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }.rail-section { padding: 22px; }.rail-section + .rail-section { border-top: 1px solid var(--line); }.rail-label { display: block; margin-bottom: 9px; color: var(--ink-muted); font-size: 12px; }.rail-section > strong { display: block; font-size: 21px; }.rail-section > p { margin: 8px 0 0; color: var(--ink-secondary); font-size: 14px; line-height: 1.7; }.rail-section.compact { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }.rail-section.compact div { display: grid; gap: 5px; }.rail-section.compact span { color: var(--ink-muted); font-size: 12px; }.rail-section.compact strong { font-size: 22px; }
.source-note { background: var(--surface-soft); }.source-note p { color: var(--ink); font-weight: 650; }.source-note small { display: block; margin-top: 7px; color: var(--ink-secondary); line-height: 1.6; }.next-steps ol { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }.next-steps li { display: flex; align-items: center; gap: 9px; color: var(--ink-secondary); font-size: 13px; }.next-steps li span { display: grid; place-items: center; width: 22px; height: 22px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 50%; font-size: 11px; font-weight: 750; }
.empty-panel { display: grid; justify-items: center; padding: 76px 24px; color: var(--ink-muted); text-align: center; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }.empty-panel > .el-icon { margin-bottom: 14px; color: var(--brand); font-size: 28px; }.empty-panel h3 { margin: 0; color: var(--ink); font-size: 17px; }.empty-panel p { margin: 8px 0 0; max-width: 58ch; line-height: 1.7; }.subject-empty { min-height: 270px; align-content: center; }.subject-create-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; max-width: 760px; margin-top: 24px; }
.table-section { padding: 24px 28px; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }
.subject-workspace { display: grid; grid-template-columns: 216px minmax(0, 1fr); gap: 18px; align-items: start; }
.subject-nav { overflow: hidden; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }
.subject-nav-heading { display: flex; justify-content: space-between; align-items: baseline; padding: 18px 18px 13px; border-bottom: 1px solid var(--line); }.subject-nav-heading strong { font-size: 15px; }.subject-nav-heading span { color: var(--ink-muted); font-size: 12px; }
.subject-nav-item { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto 14px; align-items: center; gap: 10px; width: 100%; padding: 12px 14px; color: var(--ink-secondary); background: transparent; border: 0; border-bottom: 1px solid color-mix(in oklch, var(--line) 72%, transparent); cursor: pointer; text-align: left; transition: background-color 180ms ease-out, color 180ms ease-out; }.subject-nav-item:hover { background: var(--surface-soft); }.subject-nav-item.is-active { color: var(--brand-strong); background: var(--brand-soft); }.subject-nav-item:disabled { cursor: not-allowed; opacity: .5; }.subject-avatar { display: grid; place-items: center; width: 34px; height: 34px; color: var(--ink-secondary); background: var(--surface-soft); border-radius: 8px; font-size: 13px; font-weight: 750; }.subject-nav-item.is-active .subject-avatar { color: #fff; background: var(--brand); }.subject-nav-item > span:nth-child(2) { display: grid; gap: 3px; }.subject-nav-item strong { color: var(--ink); font-size: 14px; }.subject-nav-item small { color: var(--ink-muted); font-size: 11px; }.subject-task-count { display: grid; place-items: center; min-width: 22px; height: 22px; padding: 0 5px; color: var(--ink-secondary); background: var(--surface-soft); border-radius: 999px; font-size: 11px; }.subject-nav-item .el-icon { color: var(--ink-muted); font-size: 12px; }.subject-add { display: flex; justify-content: center; padding: 11px 14px; border-top: 1px solid var(--line); }.subject-add :deep(.el-button) { width: 100%; }
.subject-detail { overflow: hidden; min-width: 0; background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); }.subject-detail-header { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 22px 26px; border-bottom: 1px solid var(--line); }.subject-detail-header > div:first-child { display: flex; align-items: center; gap: 12px; }.subject-detail-header h2 { margin: 0; font-size: 19px; }.subject-chip { padding: 6px 9px; color: #fff; background: var(--brand); border-radius: 7px; font-size: 12px; font-weight: 700; }.subject-header-actions { display: flex; align-items: center; gap: 10px; }.subject-counts { display: flex; gap: 16px; margin-right: 6px; color: var(--ink-muted); font-size: 12px; }.editing-note { display: flex; align-items: center; gap: 8px; padding: 11px 26px; color: var(--brand-strong); background: var(--brand-soft); font-size: 12px; }.editing-note .el-icon { font-size: 15px; }
.subject-section { padding: 25px 26px 27px; }.subject-section + .subject-section { border-top: 1px solid var(--line); }.subject-section-heading { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 16px; }.subject-section-heading > div { display: flex; align-items: center; gap: 9px; }.subject-section-heading .el-icon { color: var(--brand); font-size: 17px; }.subject-section-heading h3 { margin: 0; font-size: 16px; }.subject-section-heading > span { color: var(--ink-muted); font-size: 12px; }
.subject-fields { margin: 0; }.subject-fields > div { display: grid; grid-template-columns: 94px minmax(0, 1fr); gap: 18px; padding: 13px 0; border-bottom: 1px solid color-mix(in oklch, var(--line) 76%, transparent); }.subject-fields > div:last-child { border-bottom: 0; }.subject-fields dt { color: var(--ink); font-size: 13px; font-weight: 700; }.subject-fields dd { margin: 0; color: var(--ink-secondary); font-size: 14px; line-height: 1.75; overflow-wrap: anywhere; white-space: pre-wrap; text-wrap: pretty; }.plan-fields { margin-bottom: 18px; }
.subject-edit-form { display: grid; gap: 4px; }.subject-edit-form :deep(.el-form-item) { margin-bottom: 18px; }.subject-edit-form :deep(.el-form-item:last-child) { margin-bottom: 0; }.subject-edit-form :deep(.el-form-item__label) { padding-bottom: 7px; color: var(--ink); font-size: 13px; font-weight: 700; line-height: 1.4; }.subject-edit-form :deep(.el-textarea__inner) { padding: 12px 14px; color: var(--ink); background: var(--surface-soft); font-family: inherit; font-size: 14px; line-height: 1.75; resize: vertical; }.plan-edit-form { margin-bottom: 18px; }
.task-list-heading { display: flex; justify-content: space-between; align-items: center; padding-top: 17px; border-top: 1px solid var(--line); }.task-list-heading > div { display: flex; align-items: baseline; gap: 9px; }.task-list-heading strong { font-size: 13px; }.task-list-heading span { color: var(--ink-muted); font-size: 12px; }.task-edit-form { margin-top: 14px; padding: 18px; background: var(--surface-soft); border-radius: 8px; }.task-edit-form :deep(.el-form-item) { margin-bottom: 15px; }.task-edit-form :deep(.el-form-item__label) { padding-bottom: 6px; color: var(--ink); font-size: 12px; font-weight: 700; line-height: 1.4; }.task-edit-form :deep(.el-input), .task-edit-form :deep(.el-select), .task-edit-form :deep(.el-date-editor) { width: 100%; }.task-edit-form :deep(.el-textarea__inner) { line-height: 1.7; }.task-form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }.task-form-actions { display: flex; justify-content: flex-end; gap: 8px; }.task-list { margin-top: 10px; }.task-row { display: flex; justify-content: space-between; gap: 24px; padding: 14px 0; border-bottom: 1px solid color-mix(in oklch, var(--line) 76%, transparent); }.task-row:last-child { border-bottom: 0; }.task-row strong { font-size: 14px; }.task-row p { margin: 5px 0 0; color: var(--ink-muted); font-size: 12px; white-space: pre-wrap; }.task-side { display: grid; justify-items: end; align-content: start; gap: 5px; flex-shrink: 0; }.task-meta { display: flex; align-items: flex-start; gap: 8px; }.task-meta span { padding: 4px 7px; color: var(--ink-secondary); background: var(--surface-soft); border-radius: 5px; font-size: 11px; }
.checkin-form { margin-bottom: 18px; padding: 18px; background: var(--surface-soft); border-radius: 8px; }.checkin-form-grid { display: grid; grid-template-columns: minmax(0, 2fr) minmax(180px, 1fr); gap: 16px; }.checkin-form :deep(.el-form-item) { margin-bottom: 14px; }.checkin-form :deep(.el-select) { width: 100%; }.checkin-form :deep(.el-form-item__label) { color: var(--ink); font-size: 12px; font-weight: 700; }.percent-suffix { margin-left: 7px; color: var(--ink-muted); }.checkin-list { display: grid; }.checkin-row { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 18px; padding: 15px 0; border-bottom: 1px solid color-mix(in oklch, var(--line) 76%, transparent); }.checkin-row:last-child { border-bottom: 0; }.completion-rate { display: grid; align-content: center; justify-items: center; min-height: 58px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 8px; }.completion-rate strong { font-size: 17px; }.completion-rate span { margin-top: 2px; font-size: 10px; }.checkin-row > div:last-child > strong { font-size: 14px; }.checkin-row p { margin: 5px 0; color: var(--ink-secondary); line-height: 1.6; }.checkin-row time { color: var(--ink-muted); font-size: 11px; }.inline-empty { margin-top: 12px; padding: 18px; color: var(--ink-muted); background: var(--surface-soft); border-radius: 8px; text-align: center; }.inline-empty p { margin: 0; font-size: 13px; }
.review-timeline { padding: 18px 22px; background: var(--surface); border-radius: var(--radius-md); }
@media (max-width: 1100px) { .overview-layout { grid-template-columns: 1fr; }.case-rail { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }.rail-section + .rail-section { border-top: 0; border-left: 1px solid var(--line); } }
@media (max-width: 940px) { .subject-workspace { grid-template-columns: 1fr; }.subject-nav { display: flex; overflow-x: auto; }.subject-nav-heading { display: none; }.subject-nav-item { flex: 0 0 168px; border-bottom: 0; border-right: 1px solid var(--line); }.subject-nav-item:last-child { border-right: 0; } }
@media (max-width: 760px) { .case-header, .title-line { align-items: flex-start; flex-direction: column; }.title-line { gap: 4px; }.title-line h1 { font-size: 27px; }.case-actions { width: 100%; flex-wrap: wrap; }.case-actions :deep(.el-button) { flex: 1; }.case-tabs :deep(.el-tabs__item) { padding: 0 14px; }.content-section { padding: 22px 20px; }.insight-row, .target-row { grid-template-columns: 1fr; gap: 8px; }.case-rail { grid-template-columns: 1fr; }.rail-section + .rail-section { border-left: 0; border-top: 1px solid var(--line); }.subject-detail-header, .subject-section-heading, .task-row { align-items: flex-start; flex-direction: column; }.subject-detail-header, .subject-section { padding-left: 20px; padding-right: 20px; }.subject-header-actions { width: 100%; flex-wrap: wrap; }.subject-counts { width: 100%; flex-wrap: wrap; }.editing-note { padding-left: 20px; padding-right: 20px; }.subject-fields > div { grid-template-columns: 1fr; gap: 7px; }.task-form-grid { grid-template-columns: 1fr; }.task-side { justify-items: start; }.task-meta { flex-wrap: wrap; }.checkin-row { grid-template-columns: 62px minmax(0, 1fr); } }
</style>
