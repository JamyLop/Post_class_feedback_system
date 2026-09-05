<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">班级管理</text>
      <text class="p">管理班级与学生信息</text>
    </view>

    <view class="action-bar">
      <button class="btn-primary" @click="goCreateClass">新建班级</button>
      <button class="btn-outline" @click="loadData" :loading="loading" :disabled="loading">刷新</button>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <EmptyState v-else-if="!classList.length" title="暂无班级" desc="点击「新建班级」开始" />
    <view v-else class="class-list">
      <view v-for="(cls, idx) in classList" :key="cls.id" class="class-card" :class="{ 'has-border': idx > 0 }">
        <view class="class-info" @click="goStudents(cls.id, cls.name)">
          <view class="class-head">
            <text class="class-name">{{ cls.name }}</text>
            <text class="class-type">{{ cls.class_type }}</text>
          </view>
          <text class="class-meta">{{ cls.education_stage }} · {{ cls.grade }} · {{ cls.school_year }}</text>
        </view>
        <view class="class-actions">
          <text class="action-btn" @click="goStudents(cls.id, cls.name)">学生 ›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listClasses } from '../../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const classList = ref([])

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadData() {
  loading.value = true
  try {
    classList.value = await listClasses()
  } catch (e) {
    classList.value = []
  } finally {
    loading.value = false
  }
}

function goCreateClass() {
  uni.navigateTo({ url: '/subTeacher/classManager/create' })
}

function goStudents(classId, className) {
  uni.navigateTo({ url: `/subTeacher/classManager/students?classId=${classId}&className=${encodeURIComponent(className)}` })
}

onShow(() => { if (guardRole()) loadData() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.action-bar { display: flex; gap: 16rpx; }
.btn-primary {
  flex: 2; background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE;
  border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.class-card {
  background: #fff; border-radius: 12rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line); display: flex; align-items: center; justify-content: space-between;
}
.class-card.has-border { margin-top: 16rpx; }
.class-info { flex: 1; }
.class-head { display: flex; align-items: center; gap: 12rpx; }
.class-name { font-size: 30rpx; font-weight: 600; color: var(--mp-ink); }
.class-type {
  font-size: 24rpx; color: var(--mp-primary); background: var(--mp-soft);
  padding: 4rpx 10rpx; border-radius: 14rpx;
}
.class-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.class-actions { margin-left: 16rpx; }
.action-btn {
  font-size: 24rpx; color: var(--mp-primary); font-weight: 500;
  padding: 10rpx 16rpx; background: var(--mp-soft); border-radius: 8rpx;
}
</style>
