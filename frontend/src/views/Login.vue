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
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="用户名 / 学号 / 手机号" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>

        <el-button type="primary" :loading="loading" class="login-btn" @click="onSubmit">登录</el-button>

        <div class="card-foot">
          <span>还没有账号？</span>
          <el-link type="primary" :underline="false" @click="$router.push('/register')">去注册</el-link>
        </div>
      </el-form>
    </div>
    <div class="page-tip">试点年级专用 · 如忘记密码请联系班主任</div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { homeForRole } from '../router/roleHome'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const user = await auth.login(form.username, form.password)
    router.push(homeForRole(user.role))
  } catch (e) {
    /* 拦截器已提示 */
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
  background: #f2f3f5;
  padding: 32px 16px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border: 1px solid #e6e8eb;
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
  background: linear-gradient(90deg, #2f5bff, #7aa3ff);
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
  background: #1a2233;
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
}

.brand-name {
  font-size: 12px;
  color: #6b778d;
  letter-spacing: 0.02em;
}

.card-head h1 {
  margin: 0 0 6px;
  font-size: 21px;
  font-weight: 700;
  color: #1a2233;
  letter-spacing: -0.02em;
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
