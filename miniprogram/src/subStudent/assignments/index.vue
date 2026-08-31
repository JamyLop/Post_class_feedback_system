<template>
  <view class="page">
    <view class="head">
      <text class="h1">我的作业</text>
      <text class="p">查看作业、提交结果与学情反馈</text>
    </view>
    <view v-if="loading" class="tip">加载中…</view>
    <view v-else-if="rows.length" class="list">
      <view v-for="a in rows" :key="a.id" class="row" @click="openDetail(a.id)">
        <text class="title">{{ a.title }}</text>
        <text class="meta">{{ a.subject || '综合' }} · 截止 {{ a.due_at?.slice(0,16) || '-' }}</text>
      </view>
    </view>
    <EmptyState v-else title="暂无作业" desc="班主任尚未布置作业" />
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listAssignments } from '../../api/assignments'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const rows = ref([])

async function load() {
  loading.value = true
  try { rows.value = await listAssignments() } catch (_) { rows.value = [] } finally { loading.value = false }
}
function openDetail(id) { uni.navigateTo({ url: `/subStudent/assignmentDetail/index?id=${id}` }) }
onMounted(load)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.p { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
.list { display:flex; flex-direction:column; gap:16rpx; }
.row { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:24rpx; }
.title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; }
.meta { font-size:22rpx; color:#64748b; display:block; margin-top:6rpx; }
</style>
