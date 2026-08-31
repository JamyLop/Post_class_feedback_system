<template>
  <view class="page">
    <text class="h1">任务详情</text>
    <text class="desc">展示任务时间轴与打卡记录（由 caseDetail 跳转携带 task_id）</text>
    <EmptyState title="占位" desc="实际内容由 caseDetail 的任务列表进入，此页保留用于分享海报与深度链接" />
  </view>
</template>

<script setup>
import EmptyState from '../../components/EmptyState.vue'
</script>

<style scoped>
.page { padding:28rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.desc { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; }
</style>
