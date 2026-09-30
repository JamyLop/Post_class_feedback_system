<template>
  <div class="login-page">
    <div class="login-card">
      <div class="card-top-line"></div>
      <div class="card-head">
        <div class="brand-row">
          <span class="brand-mark">案</span>
          <span class="brand-name">一生一案 · 学业发展管理</span>
        </div>
        <h1>欢迎回来</h1>
        <p>用学校分配的账号登录，高三备考全程跟进</p>
      </div>

      <el-form :model="form" label-position="top" @keyup.enter="onSubmit">
        <el-form-item label="学号 / 教职工手机号">
          <el-input v-model="form.username" placeholder="家长请输入孩子学号，教职工请输入手机号" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="验证码">
          <div class="captcha-row">
            <el-input v-model="form.captcha_code" :disabled="captchaLoading" placeholder="输入右侧验证码" clearable maxlength="8" />
            <img
              v-if="captcha.image && !captchaLoading"
              :src="captcha.image"
              class="captcha-img"
              alt="验证码"
              title="看不清？点击刷新"
              @click="refreshCaptcha"
            />
            <el-link v-else type="primary" :underline="false" :disabled="captchaLoading" @click="refreshCaptcha">
              {{ captchaLoading ? '刷新中...' : '获取验证码' }}
            </el-link>
          </div>
        </el-form-item>

        <el-button type="primary" :loading="loading" :disabled="captchaLoading" class="login-btn" @click="onSubmit">登录</el-button>

        <div class="card-foot">
          <span>教职工注册</span>
          <el-link type="primary" :underline="false" @click="$router.push('/register')">邀请码注册</el-link>
        </div>
      </el-form>
    </div>
    <div class="page-tip">试点年级专用 · 如忘记密码请联系班主任</div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { getCaptcha } from '../api/auth'
import { homeForRole } from '../router/roleHome'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const captchaLoading = ref(false)
const form = reactive({ username: '', password: '', captcha_code: '' })
const captcha = reactive({ id: '', image: '' })

let captchaRequest = null
function fetchCaptcha() {
  if (captchaRequest) return captchaRequest
  captchaLoading.value = true
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
      /* 拦截器已提示 */
      return false
    } finally {
      captchaLoading.value = false
      captchaRequest = null
    }
  })()
  return captchaRequest
}

function refreshCaptcha() {
  if (!loading.value) fetchCaptcha()
}

onMounted(fetchCaptcha)

async function onSubmit() {
  if (loading.value || captchaLoading.value) return
  if (!form.username?.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (!captcha.id) {
    ElMessage.warning('验证码尚未加载，请点击刷新')
    return
  }
  if (!form.captcha_code) {
    ElMessage.warning('请输入验证码')
    return
  }
  loading.value = true
  try {
    const user = await auth.login(form.username.trim(), form.password, captcha.id, form.captcha_code)
    router.push(homeForRole(user.role))
  } catch (e) {
    /* 等待一次性验证码刷新完成后再恢复登录按钮。 */
    await fetchCaptcha()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--app-bg);
  padding: 32px 16px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 28px 28px 24px;
  position: relative;
  overflow: hidden;
}

.card-top-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--brand);
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
}

.brand-mark {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: var(--brand);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: var(--font-weight-heading);
}

.brand-name {
  font-size: 12px;
  color: #6b778d;
  letter-spacing: 0.02em;
}

.card-head h1 {
  margin: 0 0 6px;
  font-size: 21px;
  font-weight: var(--font-weight-heading);
  color: #1a2233;
  letter-spacing: normal;
}

.card-head p {
  margin: 0 0 22px;
  font-size: 13px;
  color: #6b778d;
  line-height: 1.5;
}

.login-card :deep(.el-form-item__label) {
  font-size: 13px;
  color: #3a455c;
  font-weight: 500;
  padding-bottom: 4px;
}

.login-card :deep(.el-input__wrapper) {
  padding: 6px 12px;
}

.login-btn {
  width: 100%;
  margin-top: 6px;
  height: 40px;
  font-size: 14px;
}

.captcha-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.captcha-row .el-input {
  flex: 1;
}

.captcha-img {
  width: 120px;
  height: 40px;
  border-radius: 6px;
  border: 1px solid #e6e8eb;
  cursor: pointer;
  object-fit: cover;
  flex-shrink: 0;
}

.card-foot {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: #6b778d;
}

.page-tip {
  margin-top: 14px;
  font-size: 12px;
  color: #9aa6b8;
}
</style>
