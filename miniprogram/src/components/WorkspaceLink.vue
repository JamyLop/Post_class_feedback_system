<template>
  <view class="workspace-link">
    <button class="back" hover-class="tap-active" @click="goHome">‹ 工作台</button>
    <text class="brand">一生一案</text>
  </view>
</template>
<script setup>
// 业务页可能由登录重启进入，回到工作台不依赖页面栈中存在上一页。
function goHome() { uni.reLaunch({ url: '/pages/index/index' }) }
</script>
<style scoped>
.workspace-link { display: flex; align-items: center; justify-content: space-between; padding-bottom: 16rpx; border-bottom: 1rpx solid var(--mp-line); }
.back { background: transparent; color: var(--mp-primary); font-size: 26rpx; padding: 12rpx 8rpx 12rpx 0; min-height: 72rpx; display: flex; align-items: center; }
.brand { color: var(--mp-muted); font-size: 23rpx; letter-spacing: 2rpx; }
</style>
