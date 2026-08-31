<template>
  <view class="page">
    <view class="head">
      <text class="h1">待办与班级进展</text>
      <text class="p">聚合逾期任务与长期未复盘档案，支持快速打卡与督查</text>
    </view>

    <view v-if="loading" class="tip">加载中…</view>
    <template v-else>
      <view class="stats">
        <view class="stat"><text class="num">{{ progress.total || 0 }}</text><text class="label">总档案</text></view>
        <view class="stat"><text class="num">{{ progress.overdue_tasks || 0 }}</text><text class="label">逾期任务</text></view>
        <view class="stat"><text class="num">{{ progress.long_unreviewed || 0 }}</text><text class="label">长期未复盘</text></view>
      </view>

      <view class="section">
        <text class="section-title">状态分布</text>
        <view class="chips">
          <text v-for="(v,k) in statusCounts" :key="k" class="chip">{{ k }}: {{ v }}</text>
        </view>
      </view>

      <view class="actions">
        <button type="primary" @click="goCheckin">快速打卡</button>
        <button plain @click="goReview">提交督查</button>
        <button plain @click="refresh">刷新</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCaseProgress } from '../../api/studentCases'

const loading = ref(false)
const progress = ref({})

const statusCounts = computed(() => {
  const keys = ['draft','pending_confirmation','revision_required','executing','pending_review','adjusted','archived']
  const out = {}
  keys.forEach(k => { if (progress.value[k] !== undefined) out[k]=progress.value[k] })
  return out
})

async function refresh() {
  loading.value = true
  try { progress.value = await getCaseProgress() } catch (_) {} finally { loading.value = false }
}
function goCheckin() { uni.navigateTo({ url: '/subTeacher/checkin/index' }) }
function goReview() { uni.navigateTo({ url: '/subTeacher/reviewCreate/index' }) }

onMounted(refresh)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.p { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
.stats { display:flex; gap:16rpx; }
.stat { flex:1; background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:24rpx; text-align:center; }
.num { font-size:36rpx; font-weight:700; color:#0f172a; display:block; }
.label { font-size:22rpx; color:#64748b; display:block; margin-top:4rpx; }
.section { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:24rpx; }
.section-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; margin-bottom:12rpx; }
.chips { display:flex; flex-wrap:wrap; gap:12rpx; }
.chip { font-size:22rpx; padding:8rpx 14rpx; background:#f1f5f9; border-radius:999rpx; color:#334155; }
.actions { display:flex; flex-direction:column; gap:16rpx; }
</style>
