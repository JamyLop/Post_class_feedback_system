<template>
  <el-container style="height: 100%">
    <el-aside width="220px" class="aside">
      <div class="logo">课后反馈系统</div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#ccc" active-text-color="#fff">
        <el-menu-item index="/teacher/assignments">作业管理</el-menu-item>
        <el-menu-item index="/teacher/questions">题库</el-menu-item>
        <el-menu-item index="/teacher/reviews">教师复核</el-menu-item>
        <el-menu-item index="/teacher/classes">班级管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ auth.user?.name }}</span>
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
