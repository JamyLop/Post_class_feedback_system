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
  font-size: 24rpx;
  font-weight: 500;
  background: var(--mp-soft);
  color: var(--mp-primary);
}
.tag.is-executing { background: #EAF3EE; color: #286349; }
.tag.is-pending_confirmation, .tag.is-pending_review { background: #FBF1DF; color: #865C1E; }
.tag.is-revision_required { background: #FAECE9; color: #A33E39; }
.tag.is-adjusted { background: var(--mp-soft); color: #286349; }
.tag.is-archived { background: var(--mp-soft); color: var(--mp-muted); }
.dot { width: 10rpx; height: 10rpx; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.txt { white-space: nowrap; }
</style>
