<template>
  <el-container style="height: 100%">
    <el-aside width="220px" class="aside">
      <div class="logo">学生学习中心</div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#ccc" active-text-color="#fff">
        <el-sub-menu index="learning-data" open>
          <template #title>我的学习</template>
          <el-menu-item index="/student/assignments">我的作业</el-menu-item>
          <el-menu-item index="/student/my-analytics">我的学情</el-menu-item>
          <el-menu-item index="/student/my-feedback">课后反馈</el-menu-item>
          <el-menu-item index="/student/my-weekly-scores">周测成绩</el-menu-item>
          <el-menu-item index="/student/my-monthly-reports">月报</el-menu-item>
        </el-sub-menu>
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
