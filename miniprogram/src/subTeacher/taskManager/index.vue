<template>
  <view class="page">
    <view v-if="loading" class="tip">加载中…</view>
    <template v-else>
      <view class="head">
        <text class="h1">任务管理</text>
        <text class="p">{{ detail?.student_name || '' }} · {{ detail?.class_name || '' }}</text>
      </view>

      <view v-if="detail?.tasks?.length" class="list">
        <view v-for="task in detail.tasks" :key="task.id" class="task-card">
          <view class="task-top" @click="editTask(task)">
            <view class="task-info">
              <text class="subject-tag">{{ task.subject || '综合' }}</text>
              <text class="task-title">{{ task.title }}</text>
            </view>
            <text class="task-status" :class="`is-${task.status}`">{{ taskStatusLabel(task.status) }}</text>
          </view>
          <text class="task-meta">{{ task.starts_on }} 至 {{ task.due_on }} · {{ cadenceLabel(task.cadence) }}</text>
          <text class="task-desc">{{ task.description || '暂无描述' }}</text>
          <view class="task-actions">
            <text class="link" @click="goCheckin(task.id)">打卡</text>
          </view>
        </view>
      </view>
      <view v-else class="empty">暂无任务</view>

      <button type="primary" @click="addTask">+ 新建任务</button>

      <view v-if="showForm" class="modal-mask" @click.self="showForm=false">
        <view class="modal">
          <text class="modal-title">{{ editingTask ? '编辑任务' : '新建任务' }}</text>
          <view class="form">
            <text class="label">学科</text>
            <picker :range="allSubjects" @change="e => taskForm.subject = allSubjects[e.detail.value]">
              <view class="picker">{{ taskForm.subject || '综合' }}</view>
            </picker>
            <text class="label">标题 *</text>
            <input v-model="taskForm.title" class="input" placeholder="任务标题" />
            <text class="label">描述</text>
            <textarea v-model="taskForm.description" class="textarea" placeholder="任务详细说明" />
            <text class="label">频率 *</text>
            <picker :range="cadences" range-key="label" @change="e => taskForm.cadence = cadences[e.detail.value].value">
              <view class="picker">{{ cadenceLabel(taskForm.cadence) }}</view>
            </picker>
            <text class="label">开始日期 *</text>
            <picker mode="date" @change="e => taskForm.starts_on = e.detail.value">
              <view class="picker">{{ taskForm.starts_on || '选择日期' }}</view>
            </picker>
            <text class="label">截止日期 *</text>
            <picker mode="date" @change="e => taskForm.due_on = e.detail.value">
              <view class="picker">{{ taskForm.due_on || '选择日期' }}</view>
            </picker>
          </view>
          <view class="modal-btns">
            <button plain @click="showForm=false">取消</button>
            <button type="primary" :loading="saving" @click="saveTask">保存</button>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, createTask, updateTask } from '../../api/studentCases'

const loading = ref(false)
const saving = ref(false)
const detail = ref(null)
const showForm = ref(false)
const editingTask = ref(null)
const allSubjects = ['语文','数学','英语','物理','化学','生物','政治','历史','地理']
const cadences = [{ value: 'daily', label: '日计划' }, { value: 'weekly', label: '周计划' }, { value: 'monthly', label: '月计划' }]
const taskForm = reactive({ subject: '', title: '', description: '', cadence: 'weekly', starts_on: '', due_on: '' })

function getCaseId() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options?.caseId || cur.$page?.options?.caseId
}

function cadenceLabel(v) { return { daily:'日计划', weekly:'周计划', monthly:'月计划' }[v] || v }
function taskStatusLabel(v) { return { pending:'待执行', in_progress:'执行中', completed:'已完成', cancelled:'已取消' }[v] || v }

async function load() {
  loading.value = true
  try {
    const id = getCaseId()
    if (!id) throw new Error('缺少 caseId')
    detail.value = await getStudentCase(id)
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loading.value = false }
}

function addTask() {
  editingTask.value = null
  taskForm.subject = ''
  taskForm.title = ''
  taskForm.description = ''
  taskForm.cadence = 'weekly'
  taskForm.starts_on = ''
  taskForm.due_on = ''
  showForm.value = true
}

function editTask(task) {
  editingTask.value = task
  taskForm.subject = task.subject || ''
  taskForm.title = task.title || ''
  taskForm.description = task.description || ''
  taskForm.cadence = task.cadence || 'weekly'
  taskForm.starts_on = task.starts_on || ''
  taskForm.due_on = task.due_on || ''
  showForm.value = true
}

async function saveTask() {
  if (!taskForm.title) return uni.showToast({ title: '请填写标题', icon: 'none' })
  if (!taskForm.starts_on || !taskForm.due_on) return uni.showToast({ title: '请选择日期', icon: 'none' })
  saving.value = true
  try {
    const data = { subject: taskForm.subject, title: taskForm.title, description: taskForm.description, cadence: taskForm.cadence, starts_on: taskForm.starts_on, due_on: taskForm.due_on }
    if (editingTask.value) {
      await updateTask(getCaseId(), editingTask.value.id, data)
    } else {
      await createTask(getCaseId(), data)
    }
    showForm.value = false
    uni.showToast({ title: '已保存', icon: 'success' })
    detail.value = await getStudentCase(getCaseId())
  } catch (e) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  } finally { saving.value = false }
}

function goCheckin(taskId) { uni.navigateTo({ url: `/subTeacher/checkin/index?caseId=${getCaseId()}&taskId=${taskId}` }) }

onShow(() => load())
onMounted(load)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:16rpx; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
.head { margin-bottom:4rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.p { font-size:24rpx; color:#64748b; display:block; margin-top:4rpx; }
.list { display:flex; flex-direction:column; gap:12rpx; }
.task-card { background:#fff; border:1rpx solid #e2e8f0; border-radius:12rpx; padding:18rpx; }
.task-top { display:flex; justify-content:space-between; align-items:center; }
.task-info { display:flex; gap:10rpx; align-items:center; flex:1; }
.subject-tag { font-size:20rpx; color:#2563eb; background:#eff6ff; border:1rpx solid #bfdbfe; padding:4rpx 10rpx; border-radius:999rpx; flex-shrink:0; }
.task-title { font-size:26rpx; font-weight:600; color:#0f172a; }
.task-status { font-size:20rpx; padding:4rpx 10rpx; border-radius:999rpx; background:#f1f5f9; color:#64748b; flex-shrink:0; }
.task-status.is-in_progress { background:#eff6ff; color:#2563eb; }
.task-status.is-completed { background:#ecfdf5; color:#065f46; }
.task-meta { font-size:22rpx; color:#94a3b8; display:block; margin-top:6rpx; }
.task-desc { font-size:24rpx; color:#475569; display:block; margin-top:6rpx; line-height:1.5; }
.task-actions { display:flex; gap:16rpx; margin-top:10rpx; }
.link { font-size:22rpx; color:#2563eb; }
.empty { text-align:center; color:#94a3b8; padding:32rpx; font-size:24rpx; }
.modal-mask { position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.4); display:flex; align-items:flex-end; z-index:999; }
.modal { background:#fff; border-radius:16rpx 16rpx 0 0; padding:28rpx; width:100%; max-height:80vh; overflow-y:auto; display:flex; flex-direction:column; gap:14rpx; }
.modal-title { font-size:30rpx; font-weight:700; color:#0f172a; }
.form { display:flex; flex-direction:column; gap:12rpx; }
.label { font-size:24rpx; font-weight:600; color:#0f172a; }
.input { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:16rpx 18rpx; font-size:26rpx; background:#fff; }
.textarea { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:16rpx 18rpx; font-size:26rpx; min-height:100rpx; background:#fff; }
.picker { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:16rpx 18rpx; background:#fff; font-size:26rpx; color:#334155; }
.modal-btns { display:flex; gap:12rpx; margin-top:8rpx; }
.modal-btns button { flex:1; }
</style>
