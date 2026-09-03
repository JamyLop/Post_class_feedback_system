<template>
  <view class="tag" :class="`is-${status}`">
    <text class="dot"></text>
    <text class="txt">{{ label }}</text>
  </view>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const map = {
  draft: '草稿',
  pending_confirmation: '待审查',
  revision_required: '待整改',
  executing: '执行中',
  pending_review: '待复盘',
  adjusted: '已调整',
  archived: '已归档',
}
const label = computed(() => map[props.status] || props.status)
</script>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 6rpx 16rpx;
  border-radius: 6rpx;
  font-size: 22rpx;
  font-weight: 500;
  background: #E4EEEE;
  color: #1F4F55;
}
.tag.is-executing { background: #E0F0E7; color: #2E7D5B; }
.tag.is-pending_confirmation, .tag.is-pending_review { background: #F8E8B8; color: #8A641C; }
.tag.is-revision_required { background: #F7E0D9; color: #9C4E3F; }
.tag.is-adjusted { background: #DDEBE8; color: #2E7D5B; }
.tag.is-archived { background: #E8ECEB; color: #6C7C7F; }
.dot { width: 10rpx; height: 10rpx; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.txt { white-space: nowrap; }
</style>
