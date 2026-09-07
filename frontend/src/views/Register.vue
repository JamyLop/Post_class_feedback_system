<template>
  <div class="register-page">
    <div class="register-card">
      <div class="card-top-line"></div>
      <div class="card-head">
        <div class="brand-row">
          <span class="brand-mark">案</span>
          <span class="brand-name">一生一案 · 学业发展管理</span>
        </div>
        <h1>注册账号</h1>
        <p>填写邀请码与个人信息，选择对应身份完成注册</p>
      </div>

      <el-form :model="form" label-position="top" @keyup.enter="onSubmit">
        <el-form-item label="身份">
          <el-radio-group v-model="form.role" class="role-group">
            <el-radio-button value="student">学生</el-radio-button>
            <el-radio-button value="teacher">班主任</el-radio-button>
            <el-radio-button value="subject_teacher">任课老师</el-radio-button>
            <el-radio-button value="deyu_director">德育主任</el-radio-button>
            <el-radio-button value="consultant">咨询老师</el-radio-button>
            <el-radio-button value="parent">家长</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="邀请码">
          <el-input v-model="form.invite_code" placeholder="输入年级组发放的邀请码" clearable />
        </el-form-item>

        <el-form-item v-if="form.role === 'subject_teacher'" label="教授学科">
          <el-select v-model="form.subject" placeholder="请选择您教授的学科" style="width: 100%">
            <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>

        <div class="grid-2">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="学号 / 工号，3-64位" clearable />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="form.name" placeholder="请输入姓名" clearable />
          </el-form-item>
        </div>

        <div class="grid-2">
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password placeholder="至少6位" />
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入" />
          </el-form-item>
        </div>

        <el-form-item label="验证码">
          <div class="captcha-row">
            <el-input v-model="form.captcha_code" placeholder="输入右侧验证码" clearable maxlength="8" />
            <img
              v-if="captcha.image"
              :src="captcha.image"
              class="captcha-img"
              alt="验证码"
              title="看不清？点击刷新"
              @click="fetchCaptcha"
            />
            <el-link v-else type="primary" :underline="false" @click="fetchCaptcha">获取验证码</el-link>
          </div>
        </el-form-item>

        <el-button type="primary" :loading="loading" class="submit-btn" @click="onSubmit">完成注册</el-button>

        <div class="card-foot">
          <span>已有账号？</span>
          <el-link type="primary" :underline="false" @click="$router.push('/login')">直接登录</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCaptcha, register as registerApi } from '../api/auth'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  role: 'student',
  invite_code: '',
  username: '',
  name: '',
  password: '',
  confirm: '',
  subject: '',
  captcha_code: '',
})
const captcha = reactive({ id: '', image: '' })

async function fetchCaptcha() {
  try {
    const data = await getCaptcha()
    captcha.id = data.captcha_id
    captcha.image = data.image
    form.captcha_code = ''
  } catch (e) {
    /* 拦截器已提示 */
  }
}

onMounted(fetchCaptcha)

const subjectOptions = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']

async function onSubmit() {
  if (!form.invite_code || !form.username || !form.name || !form.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.role === 'subject_teacher' && !form.subject) {
    ElMessage.warning('请选择您教授的学科')
    return
  }
  if (form.password !== form.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (!form.captcha_code) {
    ElMessage.warning('请输入验证码')
    return
  }
  loading.value = true
  try {
    const payload = {
      role: form.role,
      invite_code: form.invite_code.trim(),
      username: form.username.trim(),
      name: form.name.trim(),
      password: form.password,
      captcha_id: captcha.id,
      captcha_code: form.captcha_code.trim(),
    }
    if (form.role === 'subject_teacher') {
      payload.subject = form.subject
    }
    await registerApi(payload)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    /* 验证码一次性消费，失败后自动刷新 */
    fetchCaptcha()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f2f3f5;
  padding: 28px 16px;
}

.register-card {
  width: 100%;
  max-width: 560px;
  background: #fff;
  border: 1px solid #e6e8eb;
  border-radius: 14px;
  padding: 28px 28px 22px;
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
  margin-bottom: 16px;
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
}

.card-head h1 {
  margin: 0 0 5px;
  font-size: 20px;
  font-weight: 700;
  color: #1a2233;
}

.card-head p {
  margin: 0 0 18px;
  font-size: 13px;
  color: #6b778d;
}

.register-card :deep(.el-form-item__label) {
  font-size: 13px;
  color: #3a455c;
  font-weight: 500;
}

.role-group {
  width: 100%;
  display: flex;
}
.role-group :deep(.el-radio-button) { flex: 1; }
.role-group :deep(.el-radio-button__inner) { width: 100%; }

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
  height: 40px;
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
  margin-top: 14px;
  display: flex;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: #6b778d;
}

@media (max-width: 560px) {
  .grid-2 { grid-template-columns: 1fr; gap: 0; }
}
</style>
