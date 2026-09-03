<template>
  <view class="page">
    <view class="head">
      <text class="h1">新建班级</text>
      <text class="p">创建一个新的班级</text>
    </view>

    <view class="card">
      <text class="card-title">班级信息</text>
      <view class="form">
        <view class="field">
          <text class="field-label">班级名称 <text class="required">*</text></text>
          <input v-model="form.name" placeholder="如：高三(1)班" class="input" />
        </view>
        <view class="field">
          <text class="field-label">学段 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="s in stageOptions"
              :key="s"
              class="radio-item"
              :class="{ active: form.education_stage === s }"
              @click="form.education_stage = s; form.grade = ''"
            >
              <text class="radio-label">{{ s }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">年级 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="g in gradeOptions"
              :key="g"
              class="radio-item"
              :class="{ active: form.grade === g }"
              @click="form.grade = g"
            >
              <text class="radio-label">{{ g }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">班级类型 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="t in typeOptions"
              :key="t"
              class="radio-item"
              :class="{ active: form.class_type === t }"
              @click="form.class_type = t"
            >
              <text class="radio-label">{{ t }}</text>
            </view>
          </view>
        </view>
        <view class="field" v-if="form.class_type === '短期班'">
          <text class="field-label">短期类型 <text class="required">*</text></text>
          <view class="radio-group">
            <view
              v-for="st in shortTypeOptions"
              :key="st"
              class="radio-item"
              :class="{ active: form.short_term_type === st }"
              @click="form.short_term_type = st"
            >
              <text class="radio-label">{{ st }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">学年</text>
          <input v-model="form.school_year" placeholder="如：2026-2027" class="input" />
        </view>
      </view>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" @click="handleSubmit">
        {{ submitting ? '创建中...' : '创建班级' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { createClass } from '../../api/classes'

const submitting = ref(false)

const stageOptions = ['初中', '高中']
const gradeMap = {
  '初中': ['初一', '初二', '初三'],
  '高中': ['高一', '高二', '高三'],
}
const typeOptions = ['全年班', '短期班', '集训班', '1V1']
const shortTypeOptions = ['暑假班', '寒假班']

const form = reactive({
  name: '',
  education_stage: '高中',
  grade: '高三',
  class_type: '全年班',
  short_term_type: null,
  school_year: '2026-2027',
})

const gradeOptions = computed(() => gradeMap[form.education_stage] || [])

function validate() {
  if (!form.name.trim()) {
    uni.showToast({ title: '请输入班级名称', icon: 'none' })
    return false
  }
  if (!form.education_stage) {
    uni.showToast({ title: '请选择学段', icon: 'none' })
    return false
  }
  if (!form.grade) {
    uni.showToast({ title: '请选择年级', icon: 'none' })
    return false
  }
  if (!form.class_type) {
    uni.showToast({ title: '请选择班级类型', icon: 'none' })
    return false
  }
  if (form.class_type === '短期班' && !form.short_term_type) {
    uni.showToast({ title: '请选择短期类型', icon: 'none' })
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    await createClass({
      name: form.name.trim(),
      education_stage: form.education_stage,
      grade: form.grade,
      class_type: form.class_type,
      short_term_type: form.short_term_type,
      school_year: form.school_year || '2026-2027',
    })
    uni.showToast({ title: '创建成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; margin-bottom: 14rpx; }

.form { display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 8rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: #4A4763; }
.required { color: #EF4444; }
.input {
  border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 18rpx 22rpx; font-size: 28rpx; background: #fff;
}

.radio-group { display: flex; flex-wrap: wrap; gap: 12rpx; }
.radio-item {
  padding: 14rpx 24rpx; border-radius: 8rpx;
  border: 1rpx solid #CCD8D6; background: #fff;
}
.radio-item.active { border-color: #1F4F55; background: #DDEBE8; }
.radio-label { font-size: 26rpx; color: #4A4763; }
.radio-item.active .radio-label { color: #1F4F55; font-weight: 600; }

.submit-bar {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid #E0E7E5;
}
.btn-submit {
  background: #1F4F55; color: #fff; border-radius: 8rpx;
  padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none;
}
.btn-submit::after { border: none; }
</style>
