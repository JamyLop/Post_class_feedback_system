<template>
  <view class="page">
    <text class="h1">快速打卡</text>
    <view class="form">
      <input v-model="form.task_id" placeholder="任务 ID" class="input" type="number" />
      <input v-model.number="form.completion_rate" placeholder="完成度 0-100" class="input" type="number" />
      <textarea v-model="form.self_check" placeholder="班主任记录：实际执行情况、问题与要求" class="textarea" />
    </view>
    <button type="primary" :loading="loading" @click="submit">提交打卡</button>
    <text class="tip">完成度 100 将自动标记任务完成；0-99 标记执行中（与 Web 一致）</text>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { checkinCaseTask } from '../../api/studentCases'

const loading = ref(false)
const form = reactive({ task_id: '', completion_rate: 80, self_check: '' })

async function submit() {
  if (!form.task_id) return uni.showToast({ title: '请填任务ID', icon: 'none' })
  loading.value = true
  try {
    await checkinCaseTask(form.task_id, { completion_rate: Number(form.completion_rate), self_check: form.self_check })
    uni.showToast({ title: '打卡成功', icon: 'success' })
  } finally { loading.value = false }
}
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.form { display:flex; flex-direction:column; gap:16rpx; }
.input { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; font-size:26rpx; background:#fff; }
.textarea { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; font-size:26rpx; background:#fff; min-height:160rpx; }
.tip { font-size:22rpx; color:#94a3b8; }
</style>
