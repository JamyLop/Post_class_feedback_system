<template>
  <view class="page">
    <view class="hero">
      <view class="hero-top">
        <text class="hero-logo">一生一案</text>
        <text class="hero-badge">高三学业发展记录</text>
      </view>
      <text class="hero-title">登录工作台</text>
      <text class="hero-desc">查看档案，跟进每一阶段的成长</text>

    </view>

    <!-- 账号密码登录（主要入口） -->
    <view class="card card-primary">
      <view class="card-header">

        <view class="card-text">
          <text class="card-title">账号密码登录</text>
          <text class="card-desc">使用学号 / 手机号和密码登录系统</text>
        </view>
      </view>
      <view class="form">
        <view class="field">
          <text class="field-label">用户名 / 手机号</text>
          <input v-model="form.username" placeholder="学号或11位手机号（历史用户名仍可登录）" class="input" />
        </view>
        <view class="field">
          <text class="field-label">密码</text>
          <input v-model="form.password" password placeholder="请输入密码" class="input" />
        </view>
        <view class="field">
          <text class="field-label">验证码</text>
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
      <button class="btn-primary" :loading="pwdLoading" :disabled="pwdLoading" @click="handlePasswordLogin">登录</button>
      <view class="register-row">
        <text class="register-text">还没有账号？</text>
        <text class="register-link" @click="goRegister">邀请码注册</text>
      </view>
    </view>

    <text class="footer-text">账号问题，请联系学校管理员</text>
  </view>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { getCaptcha } from '../../api/auth'

const auth = useAuthStore()
const pwdLoading = ref(false)
const form = reactive({ username: '', password: '', captcha_code: '' })
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

function routeByRole() { return '/pages/index/index' }

async function handlePasswordLogin() {
  if (pwdLoading.value) return
  if (!form.username?.trim() || !form.password) return uni.showToast({ title: '请填写用户名和密码', icon: 'none' })
  if (!form.captcha_code) return uni.showToast({ title: '请输入验证码', icon: 'none' })
  pwdLoading.value = true
  try {
    const user = await auth.login(form.username.trim(), form.password, captcha.id, form.captcha_code)
    uni.reLaunch({ url: routeByRole(user.role) })
  } catch (e) {
    // 验证码一次性消费，失败后自动刷新
    fetchCaptcha()
  } finally {
    pwdLoading.value = false
  }
}

function goRegister() {
  uni.navigateTo({ url: '/pages/register/index' })
}
</script>

<style scoped>
@import "../../styles/auth.css";
</style>
