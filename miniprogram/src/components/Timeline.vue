<template>
  <view class="timeline">
    <view v-for="(item, idx) in items" :key="idx" class="tl-item">
      <view class="tl-line">
        <view class="tl-dot" :class="{ 'is-first': idx === 0 }"></view>
        <view v-if="idx < items.length - 1" class="tl-connector"></view>
      </view>
      <view class="tl-body">
        <text class="tl-title">{{ item.title }}</text>
        <text v-if="item.desc" class="tl-desc">{{ item.desc }}</text>
        <text v-if="item.time" class="tl-time">{{ item.time }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
defineProps({ items: { type: Array, default: () => [] } })
</script>

<style scoped>
.timeline { padding-left: 8rpx; }
.tl-item { display: flex; gap: 20rpx; position: relative; }
.tl-line { display: flex; flex-direction: column; align-items: center; width: 20rpx; flex-shrink: 0; }
.tl-dot {
  width: 16rpx; height: 16rpx; border-radius: 50%;
  background: #B8B0F6; border: 3rpx solid #EEEDFD;
  flex-shrink: 0; margin-top: 6rpx; z-index: 1;
}
.tl-dot.is-first { background: #1F4F55; border-color: #DDEBE8; }
.tl-connector { width: 2rpx; flex: 1; background: #E8E6F0; margin: 4rpx 0; }
.tl-body { padding: 4rpx 0 24rpx; flex: 1; }
.tl-title { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.tl-desc { font-size: 24rpx; color: #6E6B83; margin-top: 6rpx; display: block; line-height: 1.6; }
.tl-time { font-size: 22rpx; color: #A09CB5; margin-top: 6rpx; display: block; }
</style>
