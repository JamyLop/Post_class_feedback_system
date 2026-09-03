<template>
  <view class="page">
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
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
            <view class="task-action-btn" @click="goCheckin(task.id)">
              <text>✅ 打卡</text>
            </view>
          </view>
        </view>
      </view>
      <view v-else class="empty-text">暂无任务</view>

      <button class="btn-primary" @click="addTask">+ 新建任务</button>

      <view v-if="showForm" class="modal-mask" @click.self="showForm=false">
        <view class="modal">
          <view class="modal-header">
            <text class="modal-title">{{ editingTask ? '编辑任务' : '新建任务' }}</text>
            <text class="modal-close" @click="showForm=false">✕</text>
          </view>
          <view class="form">
            <view class="field">
              <text class="label">学科</text>
              <picker :range="allSubjects" @change="e => taskForm.subject = allSubjects[e.detail.value]">
                <view class="picker">{{ taskForm.subject || '综合' }}</view>
              </picker>
            </view>
            <view class="field">
              <text class="label">标题 *</text>
              <input v-model="taskForm.title" class="input" placeholder="任务标题" />
            </view>
            <view class="field">
              <text class="label">描述</text>
              <textarea v-model="taskForm.description" class="textarea" placeholder="任务详细说明" />
            </view>
            <view class="field">
              <text class="label">频率 *</text>
              <picker :range="cadences" range-key="label" @change="e => taskForm.cadence = cadences[e.detail.value].value">
                <view class="picker">{{ cadenceLabel(taskForm.cadence) }}</view>
              </picker>
            </view>
            <view class="field">
              <text class="label">开始日期 *</text>
              <picker mode="date" @change="e => taskForm.starts_on = e.detail.value">
                <view class="picker">{{ taskForm.starts_on || '选择日期' }}</view>
              </picker>
            </view>
            <view class="field">
              <text class="label">截止日期 *</text>
              <picker mode="date" @change="e => taskForm.due_on = e.detail.value">
                <view class="picker">{{ taskForm.due_on || '选择日期' }}</view>
              </picker>
            </view>
          </view>
          <view class="modal-btns">
            <button class="btn-outline" @click="showForm=false">取消</button>
            <button class="btn-primary" :loading="saving" @click="saveTask">保存</button>
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
    if (editingTask.value) await updateTask(getCaseId(), editingTask.value.id, data)
    else await createTask(getCaseId(), data)
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
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }
.head { margin-bottom: 4rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 4rpx; }

.list { display: flex; flex-direction: column; gap: 14rpx; }
.task-card {
  background: #fff;
  border-radius: 18rpx;
  padding: 22rpx;
  box-shadow: 0 2rpx 12rpx rgba(107,92,231,0.05);
}
.task-top { display: flex; justify-content: space-between; align-items: center; }
.task-info { display: flex; gap: 10rpx; align-items: center; flex: 1; }
.subject-tag {
  font-size: 20rpx; color: #6B5CE7;
  background: #EEEDFD;
  padding: 4rpx 12rpx; border-radius: 16rpx; flex-shrink: 0;
}
.task-title { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.task-status {
  font-size: 20rpx; padding: 4rpx 12rpx; border-radius: 16rpx;
  background: #F5F3EF; color: #8E8B9E; flex-shrink: 0;
}
.task-status.is-in_progress { background: #DCFCE7; color: #16A34A; }
.task-status.is-completed { background: #D1FAE5; color: #059669; }
.task-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 8rpx; }
.task-desc { font-size: 24rpx; color: #6E6B83; display: block; margin-top: 6rpx; line-height: 1.5; }
.task-actions { display: flex; gap: 14rpx; margin-top: 12rpx; }
.task-action-btn {
  font-size: 22rpx; color: #6B5CE7;
  background: #F0EFFC;
  padding: 8rpx 18rpx; border-radius: 12rpx;
}
.empty-text { text-align: center; color: #A09CB5; padding: 36rpx; font-size: 24rpx; }

.btn-primary {
  background: linear-gradient(135deg, #6B5CE7, #8B78F0);
  color: #fff; border-radius: 14rpx; padding: 22rpx 0;
  font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  background: #fff; color: #6B5CE7;
  border: 2rpx solid #D5D0F7; border-radius: 14rpx;
  padding: 22rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }

.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(26,22,54,0.45);
  display: flex; align-items: flex-end; z-index: 999;
}
.modal {
  background: #fff; border-radius: 24rpx 24rpx 0 0;
  padding: 28rpx; width: 100%; max-height: 80vh;
  overflow-y: auto; display: flex; flex-direction: column; gap: 14rpx;
}
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 32rpx; font-weight: 700; color: #1A1636; }
.modal-close { font-size: 28rpx; color: #A09CB5; padding: 8rpx; }
.form { display: flex; flex-direction: column; gap: 12rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.label { font-size: 24rpx; font-weight: 600; color: #1A1636; }
.input {
  border: 2rpx solid #E8E6F0; border-radius: 14rpx;
  padding: 18rpx 20rpx; font-size: 26rpx; background: #fff;
}
.textarea {
  border: 2rpx solid #E8E6F0; border-radius: 14rpx;
  padding: 18rpx 20rpx; font-size: 26rpx; min-height: 100rpx; background: #fff;
}
.picker {
  border: 2rpx solid #E8E6F0; border-radius: 14rpx;
  padding: 18rpx 20rpx; background: #fff; font-size: 26rpx; color: #1A1636;
}
.modal-btns { display: flex; gap: 14rpx; margin-top: 8rpx; }
.modal-btns button { flex: 1; }
</style>
