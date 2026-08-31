<template>
  <view class="empty">
    <text class="empty-title">{{ title }}</text>
    <text class="empty-desc">{{ desc }}</text>
    <slot />
  </view>
</template>

<script setup>
defineProps({ title: String, desc: String })
</script>

<style scoped>
.empty { padding:48rpx 32rpx; text-align:center; background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; }
.empty-title { font-size:28rpx; font-weight:600; color:#0f172a; display:block; }
.empty-desc { font-size:24rpx; color:#64748b; margin-top:8rpx; display:block; line-height:1.6; }
</style>
