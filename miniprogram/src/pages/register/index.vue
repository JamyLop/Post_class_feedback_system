<template>
  <view class="page">
    <view class="hero">
      <view class="hero-top">
        <text class="hero-logo">一生一案</text>
        <text class="hero-badge">高三学业发展记录</text>
      </view>
      <text class="hero-title">新用户注册</text>
      <text class="hero-desc">使用邀请码注册账号</text>
      <view class="hero-wave"></view>
    </view>

    <view class="card">
      <view class="card-header">
        <view class="card-icon register">
          <text class="icon-text">📝</text>
        </view>
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
        <view class="field">
          <text class="field-label">用户名 <text class="required">*</text></text>
          <input v-model="form.username" placeholder="请设置登录用户名" class="input" />
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
      </view>
      <button class="btn-primary" :loading="loading" @click="handleRegister">注册</button>
      <view class="login-row">
        <text class="login-text">已有账号？</text>
        <text class="login-link" @click="goLogin">返回登录</text>
      </view>
    </view>

    <text class="footer-text">注册后可使用账号密码登录系统</text>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const loading = ref(false)

const roleOptions = [
  { label: '学生', value: 'student' },
  { label: '家长', value: 'parent' },
  { label: '班主任', value: 'teacher' },
  { label: '德育主任', value: 'deyu_director' },
]

const form = reactive({
  invite_code: '',
  role: 'student',
  username: '',
  name: '',
  password: '',
  confirmPassword: '',
})

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
  if (!form.name.trim()) {
    uni.showToast({ title: '请输入姓名', icon: 'none' })
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
  return true
}

async function handleRegister() {
  if (!validate()) return
  loading.value = true
  try {
    await auth.register({
      invite_code: form.invite_code.trim(),
      role: form.role,
      username: form.username.trim(),
      name: form.name.trim(),
      password: form.password,
    })
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
    // 错误已由 request 拦截器处理
  } finally {
    loading.value = false
  }
}

function goLogin() {
  uni.navigateBack()
}
</script>

<style scoped>
.page { padding: 0 28rpx 48rpx; display: flex; flex-direction: column; gap: 24rpx; }

.hero {
  background: #1F4F55;
  border-radius: 12rpx;
  padding: 48rpx 32rpx 40rpx;
  color: #fff;
  position: relative;
  overflow: hidden;
  margin-top: 20rpx;
}
.hero::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 8rpx; background: #F3C969; }
.hero-top { display: flex; align-items: center; gap: 14rpx; }
.hero-logo { font-size: 30rpx; font-weight: 700; letter-spacing: 2rpx; }
.hero-badge { font-size: 22rpx; color: #DDEBE8; font-weight: 500; }
.hero-title { font-size: 40rpx; font-weight: 700; display: block; margin-top: 20rpx; }
.hero-desc { font-size: 26rpx; color: rgba(255,255,255,0.75); display: block; margin-top: 8rpx; }

.card {
  background: #fff;
  border-radius: 10rpx;
  padding: 28rpx;
  border: 1rpx solid #E0E7E5;
}

.card-header { display: flex; align-items: center; gap: 16rpx; margin-bottom: 20rpx; }
.card-icon {
  width: 72rpx; height: 72rpx;
  border-radius: 18rpx;
  display: flex; align-items: center; justify-content: center;
}
.card-icon.register { background: #E8E6F0; }
.icon-text { font-size: 32rpx; }
.card-text { flex: 1; }
.card-title { font-size: 30rpx; font-weight: 600; color: #1A1636; display: block; }
.card-desc { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 2rpx; }

.form { display: flex; flex-direction: column; gap: 16rpx; margin-bottom: 20rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: #4A4763; }
.required { color: #EF4444; }
.input {
  border: 1rpx solid #CCD8D6;
  border-radius: 8rpx;
  padding: 20rpx 22rpx;
  font-size: 28rpx;
  background: #fff;
}

.role-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.role-option {
  padding: 14rpx 24rpx;
  border-radius: 8rpx;
  border: 1rpx solid #CCD8D6;
  background: #fff;
}
.role-option.active {
  border-color: #1F4F55;
  background: #DDEBE8;
}
.role-label { font-size: 26rpx; color: #4A4763; }
.role-option.active .role-label { color: #1F4F55; font-weight: 600; }

.btn-primary {
  background: #1F4F55;
  color: #fff;
  border-radius: 8rpx;
  padding: 24rpx 0;
  font-size: 30rpx;
  font-weight: 600;
  border: none;
}
.btn-primary::after { border: none; }

.login-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  margin-top: 16rpx;
}
.login-text { font-size: 24rpx; color: #8E8B9E; }
.login-link { font-size: 24rpx; color: #1F4F55; font-weight: 600; }

.footer-text { text-align: center; font-size: 22rpx; color: #899799; padding: 8rpx 0; }
</style>
