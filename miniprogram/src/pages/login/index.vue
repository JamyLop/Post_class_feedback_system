<template>
  <view class="page">
    <view class="hero">
      <text class="hero-kicker">高三 · 一生一案</text>
      <text class="hero-title">一生一案学业发展</text>
      <text class="hero-desc">家长 / 学生 / 教师统一入口，微信一键登录后绑定已有账号</text>
    </view>

    <view class="card">
      <view class="card-head">
        <text class="card-title">微信登录</text>
        <text class="card-desc">优先使用微信授权，服务端通过 jscode2session 校验</text>
      </view>
      <button type="primary" class="wx-btn" :loading="wxLoading" @click="handleWxLogin">微信一键登录</button>
      <text class="tip">未绑定账号将引导完成绑定，已绑定直接进入首页</text>
      <text v-if="wxError" class="error">{{ wxError }}</text>
    </view>

    <view v-if="needBind" class="card">
      <view class="card-head">
        <text class="card-title">绑定已有账号</text>
        <text class="card-desc">bind_ticket 有效期 5 分钟，服务端一次性校验</text>
      </view>
      <view class="form">
        <input v-model="form.username" placeholder="手机号 / 用户名" class="input" />
        <input v-model="form.password" password placeholder="密码" class="input" />
        <text v-if="bindTicket" class="ticket">bind_ticket: {{ bindTicket.slice(0,16) }}...</text>
      </view>
      <button type="primary" plain :loading="bindLoading" @click="handleBind">确认绑定</button>
      <button plain class="mt" @click="goRegister">无账号？使用邀请码注册</button>
    </view>

    <view class="card ghost">
      <text class="ghost-title">账号密码登录（备用）</text>
      <view class="form">
        <input v-model="form.username" placeholder="用户名" class="input" />
        <input v-model="form.password" password placeholder="密码" class="input" />
      </view>
      <button @click="handlePasswordLogin" :loading="pwdLoading">账号密码登录</button>
    </view>
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

function routeByRole(role) {
  if (role === 'parent') return '/subParent/children/index'
  if (role === 'student') return '/subStudent/assignments/index'
  if (role === 'teacher' || role === 'deyu_director' || role === 'admin') return '/subTeacher/todo/index'
  return '/pages/index/index'
}

async function handleWxLogin() {
  wxError.value = ''
  wxLoading.value = true
  try {
    const loginRes = await new Promise((resolve, reject) => {
      uni.login({ provider: 'weixin', success: resolve, fail: reject })
    })
    const code = loginRes.code
    if (!code) throw new Error('获取微信 code 失败（开发工具请勾选“不校验合法域名”并检查 AppID）')
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
    // 网络层失败：真机 localhost、域名未加白、服务未启动
    if (status === 0 || msg.includes('request:fail') || msg.includes('网络')) {
      wxError.value = msg.includes('localhost') ? '网络异常：真机无法访问 localhost，请将 VITE_API_BASE 改为局域网 IP 或 HTTPS' : '网络异常，请检查 VITE_API_BASE 与微信合法域名配置'
      uni.showToast({ title: wxError.value.slice(0, 40), icon: 'none' })
      return
    }
    // AppID / 微信服务配置错误：不展开绑定，避免误导
    if (msg.includes('AppID') || msg.includes('appid') || msg.includes('微信') || msg.includes('secret') || msg.includes('jscode2session') || status === 400 && msg.includes('code')) {
      wxError.value = msg.slice(0, 80) || '微信登录配置错误，请联系管理员检查 AppID/Secret'
      uni.showToast({ title: wxError.value.slice(0, 40), icon: 'none' })
      return
    }
    // 仅开发工具无真实 code 时，允许走账号密码绑定兜底
    if (msg.includes('mock') || msg.includes('获取微信 code 失败')) {
      wxError.value = '开发工具未获取到 code，可直接使用下方账号密码登录'
      uni.showToast({ title: wxError.value.slice(0, 40), icon: 'none' })
      return
    }
    // 其他未知错误：不自动展开绑定，仅提示
    wxError.value = msg.slice(0, 80) || '微信登录失败，可使用账号密码登录'
    uni.showToast({ title: wxError.value.slice(0, 40), icon: 'none' })
  } finally {
    wxLoading.value = false
  }
}

async function handleBind() {
  if (!form.username || !form.password) return uni.showToast({ title: '请填写账号密码', icon: 'none' })
  bindLoading.value = true
  try {
    const user = await auth.wxBind({ bind_ticket: bindTicket.value, username: form.username, password: form.password })
    uni.showToast({ title: '绑定成功', icon: 'success' })
    uni.reLaunch({ url: routeByRole(user.role) })
  } catch (e) {
    // 错误由 request 拦截器已提示
  } finally {
    bindLoading.value = false
  }
}

async function handlePasswordLogin() {
  if (!form.username || !form.password) return uni.showToast({ title: '请填写账号', icon: 'none' })
  pwdLoading.value = true
  try {
    const user = await auth.login(form.username, form.password)
    uni.reLaunch({ url: routeByRole(user.role) })
  } finally {
    pwdLoading.value = false
  }
}

function goRegister() {
  uni.showToast({ title: '请在 Web 端使用邀请码注册后回此页绑定', icon: 'none' })
}
</script>

<style scoped>
.page { padding:32rpx 28rpx 48rpx; display:flex; flex-direction:column; gap:24rpx; }
.hero { background:#0f172a; color:#fff; border-radius:16rpx; padding:32rpx 28rpx; }
.hero-kicker { font-size:20rpx; color:#94a3b8; }
.hero-title { font-size:36rpx; font-weight:700; margin-top:8rpx; display:block; }
.hero-desc { font-size:24rpx; color:#94a3b8; margin-top:8rpx; display:block; line-height:1.5; }
.card { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:28rpx; }
.card.ghost { background:#f8fafc; }
.card-head { margin-bottom:16rpx; }
.card-title { font-size:28rpx; font-weight:600; color:#0f172a; display:block; }
.card-desc { font-size:22rpx; color:#64748b; margin-top:4rpx; display:block; }
.wx-btn { background:#07c160; }
.tip { font-size:22rpx; color:#64748b; margin-top:12rpx; display:block; }
.error { font-size:22rpx; color:#dc2626; margin-top:12rpx; display:block; line-height:1.5; background:#fef2f2; border:1rpx solid #fecaca; padding:12rpx; border-radius:8rpx; }
.form { display:flex; flex-direction:column; gap:16rpx; margin:16rpx 0; }
.input { border:1rpx solid #e2e8f0; border-radius:10rpx; padding:18rpx 20rpx; font-size:26rpx; background:#fff; }
.ticket { font-size:20rpx; color:#94a3b8; font-family:monospace; }
.mt { margin-top:16rpx; }
.ghost-title { font-size:26rpx; font-weight:600; color:#334155; display:block; margin-bottom:12rpx; }
</style>
