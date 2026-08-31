<template>
  <view class="page">
    <view class="banner">
      <text class="kicker">一生一案 · 高三试点</text>
      <text class="title">学业发展工作台</text>
      <text class="desc">先呈现状态与下一步行动，再展开完整材料</text>
      <view class="role-row">
        <text class="role-chip">{{ roleLabel }}</text>
        <text class="user-name">{{ auth.user?.name || '未登录' }}</text>
      </view>
    </view>

    <view class="grid">
      <view class="entry" @click="goParent">
        <text class="entry-title">家长 · 孩子档案</text>
        <text class="entry-desc">查看已发布总案、学科方案、任务与复盘</text>
        <text class="entry-action">进入 →</text>
      </view>
      <view class="entry" @click="goStudent">
        <text class="entry-title">学生 · 作业与学情</text>
        <text class="entry-desc">作业、提交结果、周考、月报、学情</text>
        <text class="entry-action">进入 →</text>
      </view>
      <view class="entry" @click="goTeacher">
        <text class="entry-title">教师 · 待办督查</text>
        <text class="entry-desc">班级进展、逾期任务、督查提交</text>
        <text class="entry-action">进入 →</text>
      </view>
    </view>

    <view class="foot">
      <text class="foot-tip">DOCX 导出、批量导入、AI 草稿请在 Web 端完成</text>
      <button plain size="mini" @click="handleLogout">退出登录</button>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const roleMap = { parent: '家长', student: '学生', teacher: '班主任', deyu_director: '德育主任', admin: '校长' }
const roleLabel = computed(() => roleMap[auth.role] || auth.role || '访客')

function goParent() { uni.navigateTo({ url: '/subParent/children/index' }) }
function goStudent() { uni.navigateTo({ url: '/subStudent/assignments/index' }) }
function goTeacher() { uni.navigateTo({ url: '/subTeacher/todo/index' }) }
function handleLogout() { auth.logout() }
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:24rpx; }
.banner { background:#0f172a; color:#fff; border-radius:16rpx; padding:32rpx 28rpx; }
.kicker { font-size:20rpx; color:#94a3b8; }
.title { font-size:34rpx; font-weight:700; display:block; margin-top:8rpx; }
.desc { font-size:24rpx; color:#94a3b8; display:block; margin-top:6rpx; }
.role-row { margin-top:18rpx; display:flex; gap:12rpx; align-items:center; }
.role-chip { font-size:20rpx; padding:6rpx 14rpx; border-radius:999rpx; background:#1e293b; color:#93c5fd; border:1rpx solid rgba(255,255,255,0.08); }
.user-name { font-size:26rpx; font-weight:600; }
.grid { display:flex; flex-direction:column; gap:16rpx; }
.entry { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:28rpx; }
.entry-title { font-size:28rpx; font-weight:600; color:#0f172a; display:block; }
.entry-desc { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; line-height:1.5; }
.entry-action { font-size:24rpx; color:#2563eb; display:block; margin-top:12rpx; font-weight:500; }
.foot { text-align:center; display:flex; flex-direction:column; gap:16rpx; align-items:center; }
.foot-tip { font-size:22rpx; color:#94a3b8; }
</style>
