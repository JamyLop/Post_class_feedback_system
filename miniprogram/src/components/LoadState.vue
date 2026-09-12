<template>
  <view v-if="loading" class="skeleton" aria-label="正在加载">
    <view class="skeleton-line short"></view><view class="skeleton-line"></view><view class="skeleton-line medium"></view>
    <text class="status">{{ loadingText }}</text>
  </view>
  <view v-else-if="error" class="error-state">
    <text class="title">加载未完成</text><text class="message">{{ error }}</text>
    <button class="retry" @click="$emit('retry')">重新加载</button>
  </view>
</template>
<script setup>
defineProps({ loading: Boolean, error: String, loadingText: { type: String, default: '正在读取数据…' } })
defineEmits(['retry'])
</script>
<style scoped>
.skeleton, .error-state { padding: 32rpx; background: var(--mp-surface); border-radius: 16rpx; }
.skeleton-line { height: 22rpx; background: var(--mp-soft); margin-bottom: 20rpx; border-radius: 4rpx; }
.short { width: 35%; }.medium { width: 70%; }
.status, .message { font-size: 24rpx; color: var(--mp-muted); display: block; }
.title { display: block; font-size: 28rpx; font-weight: 600; margin-bottom: 8rpx; }
.retry { margin-top: 24rpx; padding: 16rpx 24rpx; min-height: 80rpx; font-size: 26rpx; color: var(--mp-primary); background: var(--mp-soft); }
</style>
