<template>
  <el-container style="height: 100%">
    <el-aside width="220px" class="aside">
      <div class="logo">课后反馈系统 · 管理台</div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#ccc" active-text-color="#fff">
        <el-menu-item index="/admin/dashboard">系统概览</el-menu-item>
        <el-menu-item index="/admin/users">用户管理</el-menu-item>
        <el-menu-item index="/admin/invite-codes">邀请码管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ auth.user?.name }}（管理员）</span>
        <el-button link type="primary" @click="$router.push('/teacher/assignments')">业务系统</el-button>
        <el-button link type="primary" @click="onLogout">退出登录</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.aside {
  background: #001529;
}
.logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: #fff;
  font-weight: 600;
}
.header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #eee;
}
</style>
