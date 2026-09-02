<template>
  <view class="page">
    <text class="h1">快速打卡</text>

    <view v-if="loadingCase" class="tip">加载档案…</view>
    <template v-else>
      <view v-if="!tasks.length" class="tip">该档案暂无可打卡任务</view>
      <template v-else>
        <view class="form">
          <text class="label">选择任务</text>
          <picker :range="tasks" range-key="label" @change="onTaskChange">
            <view class="picker">{{ selectedTaskLabel || '请选择任务' }}</view>
          </picker>

          <view v-if="selectedTask" class="task-preview">
            <text class="preview-subject">{{ selectedTask.subject || '综合' }}</text>
            <text class="preview-title">{{ selectedTask.title }}</text>
            <text class="preview-meta">{{ selectedTask.starts_on }} 至 {{ selectedTask.due_on }}</text>
          </view>

          <text class="label">完成度</text>
          <view class="rate-row">
            <slider :value="form.completion_rate" :min="0" :max="100" step="5" @change="e => form.completion_rate = e.detail.value" class="slider" />
            <text class="rate-num">{{ form.completion_rate }}%</text>
          </view>

          <text class="label">班主任记录</text>
          <textarea v-model="form.self_check" placeholder="实际执行情况、问题与要求" class="textarea" />
        </view>
        <button type="primary" :loading="submitting" @click="submit">提交打卡</button>
        <text class="tip">完成度 100% 自动标记任务完成</text>
      </template>
    </template>
  </view>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, checkinCaseTask } from '../../api/studentCases'

const loadingCase = ref(false)
const submitting = ref(false)
const detail = ref(null)
const selectedTaskId = ref(null)
const form = reactive({ completion_rate: 80, self_check: '' })

const tasks = computed(() => (detail.value?.tasks || []).map(t => ({
  ...t,
  label: `${t.subject || '综合'} · ${t.title} (${t.status})`,
})))
const selectedTask = computed(() => tasks.value.find(t => t.id === selectedTaskId.value))
const selectedTaskLabel = computed(() => selectedTask.value?.label || '')

function getParams() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options || cur.$page?.options || {}
}

function onTaskChange(e) {
  const task = tasks.value[e.detail.value]
  selectedTaskId.value = task?.id || null
}

async function load() {
  loadingCase.value = true
  try {
    const opts = getParams()
    const caseId = opts.caseId || opts.case_id
    if (!caseId) throw new Error('缺少 caseId')
    detail.value = await getStudentCase(caseId)
    // 自动选中 taskId
    const taskId = opts.taskId || opts.task_id
    if (taskId) selectedTaskId.value = Number(taskId)
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loadingCase.value = false }
}

async function submit() {
  if (!selectedTaskId.value) return uni.showToast({ title: '请选择任务', icon: 'none' })
  submitting.value = true
  try {
    await checkinCaseTask(selectedTaskId.value, { completion_rate: Number(form.completion_rate), self_check: form.self_check })
    uni.showToast({ title: '打卡成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    uni.showToast({ title: e.message || '打卡失败', icon: 'none' })
  } finally { submitting.value = false }
}

onShow(() => load())
onMounted(load)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.tip { text-align:center; color:#64748b; padding:24rpx; font-size:24rpx; }
.form { display:flex; flex-direction:column; gap:14rpx; }
.label { font-size:24rpx; font-weight:600; color:#0f172a; }
.picker { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; background:#fff; font-size:26rpx; color:#334155; }
.task-preview { background:#f8fafc; border:1rpx solid #e2e8f0; border-radius:10rpx; padding:14rpx 18rpx; }
.preview-subject { font-size:22rpx; color:#2563eb; }
.preview-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; margin-top:4rpx; }
.preview-meta { font-size:22rpx; color:#94a3b8; display:block; margin-top:4rpx; }
.rate-row { display:flex; align-items:center; gap:16rpx; }
.slider { flex:1; }
.rate-num { font-size:28rpx; font-weight:700; color:#2563eb; min-width:80rpx; text-align:right; }
.textarea { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; font-size:26rpx; min-height:160rpx; background:#fff; }
</style>
