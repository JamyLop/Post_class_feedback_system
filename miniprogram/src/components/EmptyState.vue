<template>
  <view class="empty-wrap">
    <view class="empty-icon" aria-hidden="true"><view class="document-line"></view><view class="document-line short"></view></view>
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
  border: 1rpx solid var(--mp-line);
}
.empty-icon { width: 64rpx; height: 76rpx; margin: 0 auto 24rpx; padding: 22rpx 12rpx; border: 2rpx solid #9BAAC0; border-radius: 6rpx; }
.document-line { height: 2rpx; margin-bottom: 12rpx; background: #9BAAC0; }.document-line.short { width: 70%; }
.empty-emoji { font-size: 56rpx; }
.empty-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--mp-ink);
  display: block;
}
.empty-desc {
  font-size: 24rpx;
  color: var(--mp-muted);
  margin-top: 10rpx;
  display: block;
  line-height: 1.6;
}
</style>
