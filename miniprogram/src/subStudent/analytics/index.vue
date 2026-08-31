<template>
  <view class="page">
    <text class="h1">学情分析</text>
    <text class="p">查看周测、月报与知识点掌握（轻量化卡片）</text>
    <EmptyState title="占位" desc="后续接 /api/analytics 与 /api/weekly-scores，P1 完成" />
  </view>
</template>

<script setup>
import EmptyState from '../../components/EmptyState.vue'
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:16rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.p { font-size:24rpx; color:#64748b; }
</style>
