<template>
  <view class="page">
    <view v-if="loading" class="tip">加载中…</view>
    <template v-else-if="detail">
      <text class="h1">{{ detail.title }}</text>
      <text class="meta">{{ detail.subject }} · 截止 {{ detail.due_at }}</text>
      <text class="body">{{ detail.content || detail.description }}</text>
    </template>
    <EmptyState v-else title="作业不存在" desc="可能已被移除" />
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAssignment } from '../../api/assignments'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)

async function load() {
  loading.value = true
  try {
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1]
    const id = cur.options?.id
    if (id) detail.value = await getAssignment(id)
  } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:12rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.meta { font-size:22rpx; color:#64748b; }
.body { font-size:26rpx; color:#334155; line-height:1.7; white-space:pre-wrap; margin-top:12rpx; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
</style>
