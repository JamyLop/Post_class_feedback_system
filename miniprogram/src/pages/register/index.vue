<template>
  <view class="page">
    <view class="hero">
      <view class="hero-top">
        <text class="hero-logo">一生一案</text>
        <text class="hero-badge">高三学业发展记录</text>
      </view>
      <text class="hero-title">新用户注册</text>
      <text class="hero-desc">使用邀请码注册账号</text>

    </view>

    <view class="card">
      <view class="card-header">

        <view class="card-text">
          <text class="card-title">邀请码注册</text>
          <text class="card-desc">请输入管理员提供的邀请码</text>
        </view>
      </view>
      <view class="form">
        <view class="field">
          <text class="field-label">邀请码 <text class="required">*</text></text>
          <input v-model="form.invite_code" placeholder="请输入邀请码" class="input" />
        </view>
        <view class="field">
          <text class="field-label">角色 <text class="required">*</text></text>
          <view class="role-selector">
            <view
              v-for="r in roleOptions"
              :key="r.value"
              class="role-option"
              :class="{ active: form.role === r.value }"
              @click="form.role = r.value"
            >
              <text class="role-label">{{ r.label }}</text>
            </view>
          </view>
        </view>
        <view v-if="form.role === 'subject_teacher'" class="field">
          <text class="field-label">教授学科 <text class="required">*</text></text>
          <picker :range="subjectOptions" :value="subjectIndex" @change="onSubjectChange">
            <view class="input picker-display">
              {{ form.subject || '请选择您教授的学科' }}
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">用户名 {{ form.role === 'student' ? '（学号）' : '（手机号）' }} <text class="required">*</text></text>
          <input v-model="form.username" :placeholder="form.role === 'student' ? '学生学号，由班主任生成' : '请输入11位手机号'" class="input" />
        </view>
        <view class="field">
          <text class="field-label">姓名 <text class="required">*</text></text>
          <input v-model="form.name" placeholder="请输入真实姓名" class="input" />
        </view>
        <view class="field">
          <text class="field-label">密码 <text class="required">*</text></text>
          <input v-model="form.password" password placeholder="请设置登录密码（6位以上）" class="input" />
        </view>
        <view class="field">
          <text class="field-label">确认密码 <text class="required">*</text></text>
          <input v-model="form.confirmPassword" password placeholder="请再次输入密码" class="input" />
        </view>
        <view class="field">
          <text class="field-label">验证码 <text class="required">*</text></text>
          <view class="captcha-row">
            <input v-model="form.captcha_code" placeholder="输入右侧验证码" class="input captcha-input" maxlength="8" />
            <image
              v-if="captcha.image"
              :src="captcha.image"
              class="captcha-img"
              mode="aspectFill"
              @click="fetchCaptcha"
            />
            <text v-else class="captcha-link" @click="fetchCaptcha">获取验证码</text>
          </view>
        </view>
      </view>
      <button class="btn-primary" :loading="loading" :disabled="loading" @click="handleRegister">注册</button>
      <view class="login-row">
        <text class="login-text">已有账号？</text>
        <text class="login-link" @click="goLogin">返回登录</text>
      </view>
    </view>

    <text class="footer-text">注册后可使用账号密码登录系统</text>
  </view>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { getCaptcha } from '../../api/auth'

const auth = useAuthStore()
const loading = ref(false)
const captcha = reactive({ id: '', image: '' })

async function fetchCaptcha() {
  try {
    const data = await getCaptcha()
    captcha.id = data.captcha_id
    captcha.image = data.image
    form.captcha_code = ''
  } catch (e) {
    // 错误已由 request 拦截器处理
  }
}

onMounted(fetchCaptcha)

const roleOptions = [
  { label: '学生', value: 'student' },
  { label: '家长', value: 'parent' },
  { label: '班主任', value: 'teacher' },
  { label: '任课老师', value: 'subject_teacher' },
  { label: '德育主任', value: 'deyu_director' },
  { label: '咨询老师', value: 'consultant' },
  { label: '管理员', value: 'admin' },
]

const subjectOptions = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']

const form = reactive({
  invite_code: '',
  role: 'student',
  username: '',
  name: '',
  password: '',
  confirmPassword: '',
  captcha_code: '',
  subject: '',
})

const subjectIndex = ref(-1)
function onSubjectChange(e) {
  const idx = Number(e.detail.value)
  subjectIndex.value = idx
  form.subject = subjectOptions[idx] || ''
}

function validate() {
  if (!form.invite_code.trim()) {
    uni.showToast({ title: '请输入邀请码', icon: 'none' })
    return false
  }
  if (!form.role) {
    uni.showToast({ title: '请选择角色', icon: 'none' })
    return false
  }
  if (!form.username.trim()) {
    uni.showToast({ title: '请输入用户名', icon: 'none' })
    return false
  }
  // 除学生外，其他角色注册必须使用手机号作为用户名（与后端校验一致）
  if (form.role !== 'student' && !/^1[3-9]\d{9}$/.test(form.username.trim())) {
    uni.showToast({ title: '除学生外，用户名必须为11位手机号', icon: 'none' })
    return false
  }
  if (!form.name.trim()) {
    uni.showToast({ title: '请输入姓名', icon: 'none' })
    return false
  }
  if (form.role === 'subject_teacher' && !form.subject) {
    uni.showToast({ title: '请选择您教授的学科', icon: 'none' })
    return false
  }
  if (!form.password || form.password.length < 6) {
    uni.showToast({ title: '密码至少6位', icon: 'none' })
    return false
  }
  if (form.password !== form.confirmPassword) {
    uni.showToast({ title: '两次密码不一致', icon: 'none' })
    return false
  }
  if (!form.captcha_code.trim()) {
    uni.showToast({ title: '请输入验证码', icon: 'none' })
    return false
  }
  return true
}

async function handleRegister() {
  if (!validate()) return
  loading.value = true
  try {
    const payload = {
      invite_code: form.invite_code.trim(),
      role: form.role,
      username: form.username.trim(),
      name: form.name.trim(),
      password: form.password,
      captcha_id: captcha.id,
      captcha_code: form.captcha_code.trim(),
    }
    if (form.role === 'subject_teacher') {
      payload.subject = form.subject
    }
    await auth.register(payload)
    uni.showModal({
      title: '注册成功',
      content: '账号已创建，是否立即登录？',
      confirmText: '去登录',
      cancelText: '返回',
      success(res) {
        if (res.confirm) {
          uni.reLaunch({ url: '/pages/login/index' })
        } else {
          uni.navigateBack()
        }
      }
    })
  } catch (e) {
    // 验证码一次性消费，失败后自动刷新；错误已由 request 拦截器处理
    fetchCaptcha()
  } finally {
    loading.value = false
  }
}

function goLogin() {
  uni.navigateBack()
}
</script>

<style scoped>
@import "../../styles/auth.css";
.picker-display {
  display: flex;
  align-items: center;
}
</style>
