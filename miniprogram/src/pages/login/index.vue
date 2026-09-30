<template>
  <view class="page">
    <view class="hero">
      <view class="hero-top">
        <text class="hero-logo">一生一案</text>
        <text class="hero-badge">学生学业发展记录</text>
      </view>
      <text class="hero-title">登录工作台</text>
      <text class="hero-desc">查看档案，跟进每一阶段的成长</text>

    </view>

    <!-- 账号密码登录（主要入口） -->
    <view class="card card-primary">
      <view class="card-header">

        <view class="card-text">
          <text class="card-title">账号密码登录</text>
          <text class="card-desc">家长使用孩子的学号和密码登录</text>
        </view>
      </view>
      <view class="form">
        <view class="field">
          <text class="field-label">学号 / 教职工手机号</text>
          <input v-model="form.username" placeholder="家长输入孩子学号，教职工输入手机号" class="input" />
        </view>
        <view class="field">
          <text class="field-label">密码</text>
          <input v-model="form.password" password placeholder="请输入密码" class="input" />
        </view>
        <view class="field">
          <text class="field-label">验证码</text>
          <view class="captcha-row">
            <input v-model="form.captcha_code" :disabled="captchaLoading" placeholder="输入右侧验证码" class="input captcha-input" maxlength="8" />
            <image
              v-if="captcha.image && !captchaLoading"
              :src="captcha.image"
              class="captcha-img"
              mode="aspectFill"
              @click="refreshCaptcha"
            />
            <text v-else class="captcha-link" @click="refreshCaptcha">{{ captchaLoading ? '刷新中...' : '获取验证码' }}</text>
          </view>
        </view>
      </view>
      <view class="agreement-row" @click="agreed = !agreed">
        <view class="agreement-checkbox" :class="{ checked: agreed }">
          <text v-if="agreed" class="agreement-checkmark">✓</text>
        </view>
        <view class="agreement-copy">
          <text>我已阅读并同意</text>
          <text class="agreement-link" @click.stop="openLegal('user-agreement')">《用户服务协议》</text>
          <text>和</text>
          <text class="agreement-link" @click.stop="openLegal('privacy-policy')">《隐私政策》</text>
        </view>
      </view>
      <button class="btn-primary" :loading="pwdLoading" :disabled="pwdLoading || captchaLoading || !agreed" @click="handlePasswordLogin">登录</button>
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
const captchaLoading = ref(false)
const agreed = ref(false)
const form = reactive({ username: '', password: '', captcha_code: '' })
const captcha = reactive({ id: '', image: '' })

let captchaRequest = null
function fetchCaptcha() {
  if (captchaRequest) return captchaRequest
  captchaLoading.value = true
  // 旧验证码可能已被服务端消费，刷新开始后立即作废，不能继续提交。
  captcha.id = ''
  captcha.image = ''
  form.captcha_code = ''
  captchaRequest = (async () => {
    try {
      const data = await getCaptcha()
      captcha.id = data.captcha_id
      captcha.image = data.image
      return true
    } catch (e) {
      // 错误已由 request 拦截器处理
      return false
    } finally {
      captchaLoading.value = false
      captchaRequest = null
    }
  })()
  return captchaRequest
}

function refreshCaptcha() {
  if (!pwdLoading.value) fetchCaptcha()
}

onMounted(fetchCaptcha)

function routeByRole(role) { return ['student', 'parent'].includes(role) ? '/subParent/children/index' : '/pages/index/index' }

async function handlePasswordLogin() {
  if (pwdLoading.value || captchaLoading.value) return
  if (!agreed.value) return uni.showToast({ title: '请先阅读并同意相关协议', icon: 'none' })
  if (!form.username?.trim() || !form.password) return uni.showToast({ title: '请填写用户名和密码', icon: 'none' })
  if (!captcha.id) return uni.showToast({ title: '验证码尚未加载，请点击刷新', icon: 'none' })
  if (!form.captcha_code) return uni.showToast({ title: '请输入验证码', icon: 'none' })
  pwdLoading.value = true
  try {
    const user = await auth.login(form.username.trim(), form.password, captcha.id, form.captcha_code)
    uni.reLaunch({ url: routeByRole(user.role) })
  } catch (e) {
    // 验证码一次性消费；等待新验证码就绪后再允许提交，避免重复使用旧验证码。
    await fetchCaptcha()
  } finally {
    pwdLoading.value = false
  }
}

function goRegister() {
  uni.navigateTo({ url: '/pages/register/index' })
}

function openLegal(page) {
  uni.navigateTo({ url: `/pages/legal/${page}/index` })
}
</script>

<style scoped>
@import "../../styles/auth.css";
</style>
