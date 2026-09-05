<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">学生管理</text>
      <text class="p">{{ className }}</text>
    </view>

    <view class="action-bar">
      <button class="btn-primary" @click="goAddStudent">新建学生</button>
      <button class="btn-outline" @click="loadData" :loading="loading" :disabled="loading">刷新</button>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <EmptyState v-else-if="!studentList.length" title="暂无学生" desc="点击「新建学生」添加" />
    <view v-else class="student-list">
      <view v-for="(stu, idx) in studentList" :key="stu.id" class="student-card" :class="{ 'has-border': idx > 0 }">
        <view class="student-avatar" :style="{ background: getAvatarColor(stu.name) }">
          <text class="avatar-text">{{ (stu.name || '?').slice(0, 1) }}</text>
        </view>
        <view class="student-info">
          <text class="student-name">{{ stu.name }}</text>
          <text class="student-meta">用户名: {{ stu.username }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listClassStudents } from '../../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const classId = ref(null)
const className = ref('')
const loading = ref(false)
const studentList = ref([])

const avatarColors = ['#253D61', '#F5881F', '#286349', '#E74C6F', '#3B82F6']
function getAvatarColor(name) {
  const idx = (name || '').charCodeAt(0) % avatarColors.length
  return avatarColors[idx]
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

onLoad((options) => {
  classId.value = Number(options.classId)
  className.value = decodeURIComponent(options.className || '')
})

async function loadData() {
  if (!classId.value) return
  loading.value = true
  try {
    studentList.value = await listClassStudents(classId.value)
  } catch (e) {
    studentList.value = []
  } finally {
    loading.value = false
  }
}

function goAddStudent() {
  uni.navigateTo({ url: `/subTeacher/classManager/addStudent?classId=${classId.value}&className=${encodeURIComponent(className.value)}` })
}

onMounted(() => { if (guardRole()) loadData() })
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

.student-card {
  background: #fff; border-radius: 12rpx; padding: 20rpx;
  border: 1rpx solid var(--mp-line); display: flex; align-items: center; gap: 16rpx;
}
.student-card.has-border { margin-top: 12rpx; }
.student-avatar {
  width: 72rpx; height: 72rpx; border-radius: 18rpx;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.avatar-text { color: #fff; font-size: 28rpx; font-weight: 700; }
.student-info { flex: 1; }
.student-name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.student-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
</style>
