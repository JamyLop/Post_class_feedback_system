<template>
  <view class="page">
    <view class="hero">
      <view class="hero-top">
        <text class="hero-logo">一生一案</text>
        <text class="hero-badge">高三学业发展记录</text>
      </view>
      <text class="hero-title">学业发展工作台</text>
      <text class="hero-desc">家长 / 学生 / 教师统一入口</text>
      <view class="hero-wave"></view>
    </view>

    <!-- 账号密码登录（主要入口） -->
    <view class="card card-primary">
      <view class="card-header">
        <view class="card-icon primary">
          <text class="icon-text">🔑</text>
        </view>
        <view class="card-text">
          <text class="card-title">账号密码登录</text>
          <text class="card-desc">使用用户名和密码登录系统</text>
        </view>
      </view>
      <view class="form">
        <view class="field">
          <text class="field-label">用户名</text>
          <input v-model="form.username" placeholder="请输入用户名" class="input" />
        </view>
        <view class="field">
          <text class="field-label">密码</text>
          <input v-model="form.password" password placeholder="请输入密码" class="input" />
        </view>
      </view>
      <button class="btn-primary" :loading="pwdLoading" @click="handlePasswordLogin">登录</button>
      <view class="register-row">
        <text class="register-text">还没有账号？</text>
        <text class="register-link" @click="goRegister">邀请码注册</text>
      </view>
    </view>

    <!-- 微信登录（次要入口） -->
    <view class="card">
      <view class="card-header">
        <view class="card-icon wx">
          <text class="icon-text">💬</text>
        </view>
        <view class="card-text">
          <text class="card-title">微信一键登录</text>
          <text class="card-desc">授权后自动匹配已有账号</text>
        </view>
      </view>
      <button class="btn-wx" :loading="wxLoading" @click="handleWxLogin">
        <text class="btn-wx-text">{{ wxLoading ? '登录中...' : '微信登录' }}</text>
      </button>
      <text v-if="wxError" class="error">{{ wxError }}</text>
    </view>

    <!-- 绑定已有账号（微信未绑定时显示） -->
    <view v-if="needBind" class="card">
      <view class="card-header">
        <view class="card-icon bind">
          <text class="icon-text">🔗</text>
        </view>
        <view class="card-text">
          <text class="card-title">绑定已有账号</text>
          <text class="card-desc">一次性绑定，后续自动登录</text>
        </view>
      </view>
      <view class="form">
        <view class="field">
          <text class="field-label">账号</text>
          <input v-model="bindForm.username" placeholder="手机号 / 用户名" class="input" />
        </view>
        <view class="field">
          <text class="field-label">密码</text>
          <input v-model="bindForm.password" password placeholder="请输入密码" class="input" />
        </view>
      </view>
      <button class="btn-primary" :loading="bindLoading" @click="handleBind">确认绑定</button>
    </view>

    <text class="footer-text">登录即代表同意相关服务协议</text>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const wxLoading = ref(false)
const bindLoading = ref(false)
const pwdLoading = ref(false)
const needBind = ref(false)
const bindTicket = ref('')
const wxError = ref('')
const form = reactive({ username: '', password: '' })
const bindForm = reactive({ username: '', password: '' })

function routeByRole(role) {
  if (role === 'parent') return '/subParent/children/index'
  if (role === 'student') return '/pages/student/assignments/index'
  if (role === 'teacher' || role === 'deyu_director' || role === 'admin') return '/subTeacher/todo/index'
  return '/pages/index/index'
}

async function handlePasswordLogin() {
  if (!form.username || !form.password) return uni.showToast({ title: '请填写用户名和密码', icon: 'none' })
  pwdLoading.value = true
  try {
    const user = await auth.login(form.username, form.password)
    uni.reLaunch({ url: routeByRole(user.role) })
  } catch (e) {
    // 错误已由 request 拦截器处理
  } finally {
    pwdLoading.value = false
  }
}

async function handleWxLogin() {
  wxError.value = ''
  wxLoading.value = true
  try {
    const loginRes = await new Promise((resolve, reject) => {
      uni.login({ provider: 'weixin', success: resolve, fail: reject })
    })
    const code = loginRes.code
    if (!code) throw new Error('获取微信 code 失败')
    const res = await auth.wxLogin(code)
    if (res.bound) {
      uni.showToast({ title: '登录成功', icon: 'success' })
      uni.reLaunch({ url: routeByRole(res.user.role) })
    } else {
      bindTicket.value = res.bind_ticket
      needBind.value = true
      uni.showToast({ title: '请完成绑定', icon: 'none' })
    }
  } catch (e) {
    const msg = e?.message || e?.msg || e?.errMsg || ''
    const status = e?.status
    if (status === 0 || msg.includes('request:fail') || msg.includes('网络')) {
      wxError.value = msg.includes('localhost') ? '网络异常：真机无法访问 localhost' : '网络异常，请检查配置'
    } else if (msg.includes('mock') || msg.includes('获取微信 code 失败')) {
      wxError.value = '开发工具未获取到 code，可使用账号密码登录'
    } else {
      wxError.value = msg.slice(0, 80) || '登录失败，请重试'
    }
    uni.showToast({ title: wxError.value.slice(0, 40), icon: 'none' })
  } finally {
    wxLoading.value = false
  }
}

async function handleBind() {
  if (!bindForm.username || !bindForm.password) return uni.showToast({ title: '请填写账号密码', icon: 'none' })
  bindLoading.value = true
  try {
    const user = await auth.wxBind({ bind_ticket: bindTicket.value, username: bindForm.username, password: bindForm.password })
    uni.showToast({ title: '绑定成功', icon: 'success' })
    uni.reLaunch({ url: routeByRole(user.role) })
  } catch (e) {
    // 错误已由 request 拦截器处理
  } finally {
    bindLoading.value = false
  }
}

function goRegister() {
  uni.navigateTo({ url: '/pages/register/index' })
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
.card-primary {
  border-color: #1F4F55;
  box-shadow: 0 4rpx 20rpx rgba(31,79,85,0.08);
}

.card-header { display: flex; align-items: center; gap: 16rpx; margin-bottom: 20rpx; }
.card-icon {
  width: 72rpx; height: 72rpx;
  border-radius: 18rpx;
  display: flex; align-items: center; justify-content: center;
}
.card-icon.primary { background: #DDEBE8; }
.card-icon.wx { background: #E8F5E9; }
.card-icon.bind { background: #F8E8B8; }
.icon-text { font-size: 32rpx; }
.card-text { flex: 1; }
.card-title { font-size: 30rpx; font-weight: 600; color: #1A1636; display: block; }
.card-desc { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 2rpx; }

.form { display: flex; flex-direction: column; gap: 16rpx; margin-bottom: 20rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: #4A4763; }
.input {
  border: 1rpx solid #CCD8D6;
  border-radius: 8rpx;
  padding: 20rpx 22rpx;
  font-size: 28rpx;
  background: #fff;
}

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

.btn-wx {
  background: #2E7D5B;
  border-radius: 8rpx;
  padding: 24rpx 0;
  border: none;
}
.btn-wx::after { border: none; }
.btn-wx-text { color: #fff; font-size: 30rpx; font-weight: 600; }

.register-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  margin-top: 16rpx;
}
.register-text { font-size: 24rpx; color: #8E8B9E; }
.register-link { font-size: 24rpx; color: #1F4F55; font-weight: 600; }

.error {
  font-size: 24rpx;
  color: #EF4444;
  background: #FEF2F2;
  border: 2rpx solid #FECACA;
  border-radius: 12rpx;
  padding: 16rpx;
  margin-top: 12rpx;
  line-height: 1.5;
  display: block;
}

.footer-text { text-align: center; font-size: 22rpx; color: #899799; padding: 8rpx 0; }
</style>
