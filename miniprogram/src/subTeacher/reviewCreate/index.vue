<template>
  <view class="page">
    <WorkspaceLink />
    <text class="h1">提交督查</text>

    <view v-if="loadingCase" class="loading-bar">
      <text class="loading-text">加载档案...</text>
    </view>
    <template v-else>
      <view class="card">
        <view class="field">
          <text class="label">选择档案</text>
          <picker v-if="!presetCaseId" :range="cases" range-key="label" @change="onCaseChange">
            <view class="picker">{{ selectedCaseLabel || '请选择学生档案' }}</view>
          </picker>
          <view v-else class="picker disabled">{{ selectedCaseLabel || '已指定档案' }}</view>
        </view>

        <view v-if="selectedCase" class="case-preview">
          <text class="preview-name">{{ selectedCase.student_name }}</text>
          <text class="preview-meta">{{ selectedCase.class_name }} · 第{{ selectedCase.version }}版</text>
        </view>

        <view class="field">
          <text class="label">督查层级</text>
          <picker :range="levels" range-key="label" @change="e => form.review_level = levels[e.detail.value].value">
            <view class="picker">{{ currentLevelLabel }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="label">关联学科（可选）</text>
          <picker :range="allSubjects" @change="e => form.subject = allSubjects[e.detail.value]">
            <view class="picker">{{ form.subject || '不关联学科' }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="label">整改截止日期（可选）</text>
          <picker mode="date" @change="e => form.correction_due_on = e.detail.value">
            <view class="picker">{{ form.correction_due_on || '不设截止' }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="label">发现问题</text>
          <textarea v-model="form.problem" placeholder="督查中发现的问题" class="textarea" />
        </view>

        <view class="field">
          <text class="label">整改要求</text>
          <textarea v-model="form.corrective_action" placeholder="具体整改要求" class="textarea" />
        </view>

        <view class="field">
          <text class="label">复查结果（可选）</text>
          <textarea v-model="form.recheck_result" placeholder="复查情况" class="textarea" />
        </view>
      </view>
      <button class="btn-primary" :loading="submitting" :disabled="submitting" @click="submit">提交</button>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { listStudentCases, createCaseReview } from '../../api/studentCases'

const loadingCase = ref(false)
const submitting = ref(false)
const cases = ref([])
const selectedCaseId = ref(null)
const presetCaseId = ref(null)

const levels = [
  { value: 'head_teacher', label: '班主任督查' },
  { value: 'subject', label: '学科督查' },
]
const allSubjects = ['语文','数学','英语','物理','化学','生物','政治','历史','地理']
const form = reactive({ review_level: 'head_teacher', subject: '', correction_due_on: '', problem: '', corrective_action: '', recheck_result: '' })

const selectedCase = computed(() => cases.value.find(c => c.id === selectedCaseId.value))
const selectedCaseLabel = computed(() => selectedCase.value ? `${selectedCase.value.student_name} · ${selectedCase.value.class_name}` : '')
const currentLevelLabel = computed(() => levels.find(l => l.value === form.review_level)?.label || form.review_level)

function getParams() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options || cur.$page?.options || {}
}

function onCaseChange(e) {
  selectedCaseId.value = cases.value[e.detail.value]?.id || null
}

async function load() {
  loadingCase.value = true
  try {
    const opts = getParams()
    if (opts.caseId || opts.case_id) {
      presetCaseId.value = Number(opts.caseId || opts.case_id)
      selectedCaseId.value = presetCaseId.value
    }
    const list = await listStudentCases()
    cases.value = (Array.isArray(list) ? list : []).map(c => ({
      ...c,
      label: `${c.student_name || '学生#'+c.student_id} · ${c.class_name || ''} (${c.status})`,
    }))
    if (presetCaseId.value && !selectedCase.value) {
      const found = cases.value.find(c => c.id === presetCaseId.value)
      if (found) selectedCaseId.value = found.id
    }
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loadingCase.value = false }
}

async function submit() {
  if (!selectedCaseId.value) return uni.showToast({ title: '请选择档案', icon: 'none' })
  if (!form.problem && !form.corrective_action) return uni.showToast({ title: '请填问题或整改要求', icon: 'none' })
  submitting.value = true
  try {
    await createCaseReview(selectedCaseId.value, {
      review_level: form.review_level,
      subject: form.subject,
      problem: form.problem,
      corrective_action: form.corrective_action,
      correction_due_on: form.correction_due_on || null,
      recheck_result: form.recheck_result,
    })
    uni.showToast({ title: '提交成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    uni.showToast({ title: e.message || '提交失败', icon: 'none' })
  } finally { submitting.value = false }
}

onShow(() => load())

</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  box-shadow: none;
  display: flex; flex-direction: column; gap: 18rpx;
}
.field { display: flex; flex-direction: column; gap: 8rpx; }
.label { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.picker {
  border: 2rpx solid var(--mp-line); border-radius: 14rpx;
  padding: 18rpx 20rpx; background: #fff; font-size: 26rpx; color: var(--mp-ink);
}
.picker.disabled { background: #F7F8FA; color: var(--mp-muted); }
.case-preview {
  background: #F7F8FA; border-radius: 14rpx; padding: 16rpx 20rpx;
}
.preview-name { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.preview-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.textarea {
  border: 2rpx solid var(--mp-line); border-radius: 14rpx;
  padding: 18rpx 20rpx; font-size: 26rpx; min-height: 140rpx; background: #fff;
}

.btn-primary {
  background: var(--mp-primary);
  color: #fff; border-radius: 14rpx; padding: 24rpx 0;
  font-size: 30rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
</style>
