<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">新建学生</text>
      <text class="p">仅需录入学生信息，无需选择班级，账号自动生成并关联您</text>
    </view>

    <view class="hint-card">
      <text class="hint-text">学生将进入未分班池并自动关联您为咨询老师；班主任后续在班级名册“选已有学生”将其加入班级</text>
    </view>

    <view class="card">
      <view class="form">
        <view class="field">
          <text class="field-label">姓名 <text class="required">*</text></text>
          <input v-model="form.name" placeholder="请输入学生姓名" class="input" />
        </view>
        <view class="field">
          <text class="field-label">性别</text>
          <view class="radio-group">
            <view
              v-for="g in genderOptions"
              :key="g"
              class="radio-item"
              :class="{ active: form.gender === g }"
              @click="form.gender = form.gender === g ? '' : g"
            >
              <text class="radio-label">{{ g }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">民族</text>
          <input v-model="form.ethnicity" placeholder="例如：汉族" class="input" />
        </view>
        <view class="field">
          <text class="field-label">年级</text>
          <input v-model="form.grade" placeholder="例如：高三" class="input" />
        </view>
        <view class="field">
          <text class="field-label">生源地学校</text>
          <input v-model="form.source_school" placeholder="填写学生原就读学校" class="input" />
        </view>
        <view class="field">
          <text class="field-label">宿舍号</text>
          <input v-model="form.dorm_number" placeholder="例如：3号楼205" class="input" />
        </view>
        <view class="field">
          <text class="field-label">了解渠道</text>
          <input v-model="form.channel" placeholder="选填，例如：转介绍 / 线上咨询" class="input" />
        </view>
      </view>
    </view>

    <view class="hint-card">
      <text class="hint-text">* 学生账号将自动生成（ZX临时学号），初始密码为 123456</text>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" :disabled="submitting" @click="handleSubmit">
        {{ submitting ? '创建中...' : '新建学生' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { reactive, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { createQuickStudent } from '../../api/studentCases'

const auth = useAuthStore()
const submitting = ref(false)
const genderOptions = ['男', '女']
const form = reactive({
  name: '', gender: '', ethnicity: '', grade: '',
  source_school: '', dorm_number: '', channel: '',
})

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'consultant') {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function handleSubmit() {
  if (!guardRole()) return
  if (!form.name.trim()) {
    uni.showToast({ title: '请填写学生姓名', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    await createQuickStudent({
      name: form.name.trim(),
      gender: form.gender || '',
      ethnicity: form.ethnicity.trim(),
      grade: form.grade.trim(),
      source_school: form.source_school.trim(),
      dorm_number: form.dorm_number.trim(),
      channel: form.channel.trim(),
    })
    uni.showToast({ title: '新建学生成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1200)
  } catch (_) {
    // 错误已统一提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.card { background: #fff; border-radius: 10rpx; padding: 24rpx; border: 1rpx solid var(--mp-line); }
.form { display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: var(--mp-body); }
.required { color: #A33E39; }
.input { border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 22rpx; font-size: 28rpx; background: #fff; }
.radio-group { display: flex; flex-wrap: wrap; gap: 12rpx; }
.radio-item { padding: 14rpx 24rpx; border-radius: 8rpx; border: 1rpx solid #C6D0DE; background: #fff; }
.radio-item.active { border-color: var(--mp-primary); background: var(--mp-soft); }
.radio-label { font-size: 26rpx; color: var(--mp-body); }
.radio-item.active .radio-label { color: var(--mp-primary); font-weight: 600; }
.hint-card { background: #FFF8E8; border-radius: 10rpx; padding: 18rpx; border: 1rpx solid #FBF1DF; }
.hint-text { font-size: 24rpx; color: #865C1E; display: block; line-height: 1.6; }
.submit-bar { position: fixed; left: 0; right: 0; bottom: 0; background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom)); border-top: 1rpx solid var(--mp-line); }
.btn-submit { background: var(--mp-primary); color: #fff; border-radius: 8rpx; padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none; }
.btn-submit::after { border: none; }
</style>
