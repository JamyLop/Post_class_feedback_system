<template>
  <view class="page">
    <text class="h1">提交督查</text>
    <view class="form">
      <input v-model="form.case_id" placeholder="学生总案 ID" class="input" type="number" />
      <picker :range="levels" range-key="label" @change="onLevelChange">
        <view class="picker">层级：{{ currentLevelLabel }}</view>
      </picker>
      <input v-model="form.subject" placeholder="关联学科（可选）" class="input" />
      <input v-model="form.correction_due_on" placeholder="整改截止 YYYY-MM-DD" class="input" />
      <textarea v-model="form.problem" placeholder="发现问题" class="textarea" />
      <textarea v-model="form.corrective_action" placeholder="整改要求" class="textarea" />
      <textarea v-model="form.recheck_result" placeholder="复查结果（可选）" class="textarea" />
    </view>
    <button type="primary" :loading="loading" @click="submit">提交</button>
  </view>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { createCaseReview } from '../../api/studentCases'

const levels = [
  { value: 'head_teacher', label: '班主任督查' },
  { value: 'subject', label: '学科督查' },
  { value: 'school', label: '校级督查' },
  { value: 'principal', label: '校长督察' },
]
const form = reactive({ case_id: '', review_level: 'head_teacher', subject: '', correction_due_on: '', problem: '', corrective_action: '', recheck_result: '' })
const loading = ref(false)
const currentLevelLabel = computed(() => levels.find((l)=>l.value===form.review_level)?.label || form.review_level)

function onLevelChange(e) { form.review_level = levels[e.detail.value].value }

async function submit() {
  if (!form.case_id) return uni.showToast({ title: '请填总案ID', icon: 'none' })
  if (!form.problem && !form.corrective_action) return uni.showToast({ title: '请填问题或整改要求', icon: 'none' })
  loading.value = true
  try {
    await createCaseReview(form.case_id, {
      review_level: form.review_level,
      subject: form.subject,
      problem: form.problem,
      corrective_action: form.corrective_action,
      correction_due_on: form.correction_due_on || null,
      recheck_result: form.recheck_result,
    })
    uni.showToast({ title: '提交成功', icon: 'success' })
  } finally { loading.value = false }
}
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.form { display:flex; flex-direction:column; gap:16rpx; }
.input { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; font-size:26rpx; background:#fff; }
.picker { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; background:#fff; font-size:26rpx; color:#334155; }
.textarea { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; font-size:26rpx; background:#fff; min-height:140rpx; }
</style>
