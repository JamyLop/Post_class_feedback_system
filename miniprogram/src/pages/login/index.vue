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
import { ref, reactive } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const pwdLoading = ref(false)
const form = reactive({ username: '', password: '' })

function routeByRole() { return '/pages/index/index' }

async function handlePasswordLogin() {
  if (pwdLoading.value) return
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

function goRegister() {
  uni.navigateTo({ url: '/pages/register/index' })
}
</script>

<style scoped>
@import "../../styles/auth.css";
</style>
