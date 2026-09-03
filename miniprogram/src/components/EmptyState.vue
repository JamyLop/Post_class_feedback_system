<template>
  <view class="empty-wrap">
    <view class="empty-icon">
      <text class="empty-emoji">{{ icon }}</text>
    </view>
    <text class="empty-title">{{ title }}</text>
    <text v-if="desc" class="empty-desc">{{ desc }}</text>
    <slot />
  </view>
</template>

<script setup>
defineProps({
  title: String,
  desc: String,
  icon: { type: String, default: '📭' }
})
</script>

<style scoped>
.empty-wrap {
  padding: 64rpx 40rpx;
  text-align: center;
  background: #FFFFFF;
  border-radius: 10rpx;
  border: 1rpx dashed #CBD6D4;
}
.empty-icon { margin-bottom: 20rpx; }
.empty-emoji { font-size: 56rpx; }
.empty-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #203235;
  display: block;
}
.empty-desc {
  font-size: 24rpx;
  color: #6C7C7F;
  margin-top: 10rpx;
  display: block;
  line-height: 1.6;
}
</style>
