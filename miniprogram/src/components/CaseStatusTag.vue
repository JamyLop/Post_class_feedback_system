<template>
  <view class="status-tag" :class="`is-${status}`">
    <text class="dot"></text>
    <text>{{ label }}</text>
  </view>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const map = {
  draft: '草稿',
  pending_confirmation: '待德育审查',
  revision_required: '待整改',
  executing: '执行中',
  pending_review: '待复盘',
  adjusted: '已调整',
  archived: '已归档',
}
const label = computed(() => map[props.status] || props.status)
</script>

<style scoped>
.status-tag { display:inline-flex; align-items:center; gap:6rpx; padding:4rpx 14rpx; border-radius:999rpx; font-size:22rpx; border:1rpx solid #e2e8f0; background:#f8fafc; color:#475569; }
.status-tag.is-executing { background:#eff6ff; border-color:#bfdbfe; color:#2563eb; }
.status-tag.is-pending_confirmation, .status-tag.is-pending_review { background:#fef3c7; border-color:#fde68a; color:#92400e; }
.status-tag.is-revision_required { background:#fff7ed; border-color:#fdba74; color:#9a3412; }
.status-tag.is-adjusted { background:#ecfdf5; border-color:#a7f3d0; color:#065f46; }
.status-tag.is-archived { background:#f1f5f9; color:#64748b; }
.dot { width:10rpx; height:10rpx; border-radius:50%; background: currentColor; }
</style>
