<template>
  <view class="timeline">
    <view v-for="(item, idx) in items" :key="idx" class="timeline-item">
      <view class="timeline-dot"></view>
      <view class="timeline-content">
        <text class="timeline-title">{{ item.title }}</text>
        <text class="timeline-desc">{{ item.desc }}</text>
        <text v-if="item.time" class="timeline-time">{{ item.time }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
defineProps({ items: { type: Array, default: () => [] } })
</script>

<style scoped>
.timeline { position:relative; padding-left:28rpx; }
.timeline-item { display:flex; gap:18rpx; padding:16rpx 0; border-left:2rpx solid #e2e8f0; padding-left:18rpx; position:relative; }
.timeline-item:last-child { border-left-color: transparent; }
.timeline-dot { position:absolute; left:-9rpx; top:22rpx; width:16rpx; height:16rpx; border-radius:50%; background:#2563eb; border:3rpx solid #dbeafe; }
.timeline-title { font-size:26rpx; font-weight:600; color:#0f172a; }
.timeline-desc { font-size:24rpx; color:#475569; margin-top:4rpx; display:block; line-height:1.5; }
.timeline-time { font-size:22rpx; color:#94a3b8; margin-top:6rpx; display:block; }
</style>
