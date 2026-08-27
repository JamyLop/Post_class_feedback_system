<template>
  <div class="register-wrap">
    <el-card class="register-card">
      <template #header>
        <div class="register-title">注册账号</div>
      </template>
      <el-form :model="form" label-width="70px" @keyup.enter="onSubmit">
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">教师</el-radio>
            <el-radio value="parent">家长</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="邀请码">
          <el-input v-model="form.invite_code" placeholder="请向管理员索取邀请码" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="用户名（3-64位）" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="姓名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="密码（至少6位）" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" @click="onSubmit">
            注册
          </el-button>
        </el-form-item>
        <div class="register-footer">
          已有账号？
          <el-link type="primary" @click="$router.push('/login')">去登录</el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register as registerApi } from '../api/auth'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  role: 'student',
  invite_code: '',
  username: '',
  name: '',
  password: '',
  confirm: '',
})

async function onSubmit() {
  if (!form.invite_code || !form.username || !form.name || !form.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.password !== form.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await registerApi({
      role: form.role,
      invite_code: form.invite_code.trim(),
      username: form.username.trim(),
      name: form.name.trim(),
      password: form.password,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.register-card {
  width: 420px;
}
.register-title {
  text-align: center;
  font-size: 18px;
  font-weight: 600;
}
.register-footer {
  text-align: center;
  font-size: 14px;
  color: #666;
}
</style>
