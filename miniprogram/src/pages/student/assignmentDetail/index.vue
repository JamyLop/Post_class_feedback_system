<template>
  <view class="page">
    <WorkspaceLink />
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="detail">
      <view class="header-card">
        <text class="h1">{{ detail.title }}</text>
        <view class="meta-row">
          <text class="subject-chip">{{ detail.subject }}</text>
          <text class="meta">截止 {{ detail.due_at }}</text>
        </view>
      </view>
      <view class="content-card">
        <text class="body">{{ detail.content || detail.description }}</text>
      </view>
    </template>
    <EmptyState v-else title="作业不存在" desc="可能已被移除" />
  </view>
</template>

<script setup>
import WorkspaceLink from '../../../components/WorkspaceLink.vue'
import { ref, onMounted } from 'vue'
import { getAssignment } from '../../../api/assignments'
import EmptyState from '../../../components/EmptyState.vue'

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
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.header-card {
  background: #fff; border-radius: 20rpx; padding: 28rpx;
  box-shadow: none;
}
.h1 { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.meta-row { display: flex; gap: 12rpx; align-items: center; margin-top: 12rpx; }
.subject-chip {
  font-size: 24rpx; font-weight: 500; color: var(--mp-primary);
  background: var(--mp-soft); padding: 6rpx 14rpx; border-radius: 14rpx;
}
.meta { font-size: 24rpx; color: var(--mp-muted); }

.content-card {
  background: #fff; border-radius: 20rpx; padding: 28rpx;
  box-shadow: none;
}
.body { font-size: 28rpx; color: var(--mp-body); line-height: 1.8; white-space: pre-wrap; }
</style>
