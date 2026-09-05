<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">孩子的一生一案</text>
      <text class="p">查看已发布总案、学科方案与阶段复盘</text>
    </view>

    <LoadState :loading="loading" :error="error" @retry="load" />

    <view v-if="!loading && !error && children.length" class="list">
      <view v-for="child in children" :key="child.student_id" class="child-card" @click="openCases(child)">
        <view class="avatar" :style="{ background: avatarColor(child.student_name) }">
          <text class="avatar-text">{{ (child.student_name || '孩').slice(0,1) }}</text>
        </view>
        <view class="child-info">
          <view class="title-row">
            <text class="name">{{ child.student_name }}</text>
            <CaseStatusTag v-if="child.latest_case_status" :status="child.latest_case_status" />
          </view>
          <text class="summary">{{ child.latest_case_summary || '班主任正在持续记录' }}</text>
          <text class="meta">{{ child.class_name }} · 学期 {{ child.cycle_name || '-' }}</text>
        </view>
        <text class="arrow">›</text>
      </view>
    </view>

    <EmptyState v-if="!loading && !error && !children.length" title="暂无绑定子女" desc="请联系班主任录入家长手机号" />

    <view v-if="!loading && !error && familyCases.length" class="card">
      <text class="card-title">已发布档案（{{ familyCases.length }}）</text>
      <view v-for="(c, idx) in familyCases" :key="c.id" class="case-row" :class="{ 'has-border': idx > 0 }" @click="openCase(c.id)">
        <text class="case-name">{{ c.student_name }} · 第{{ c.version }}版</text>
        <CaseStatusTag :status="c.status" />
      </view>
    </view>
    <view v-else-if="!loading && !error && children.length" class="empty-tip">
      <text>已绑定子女，但暂无已发布档案</text>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getMyChildren } from '../../api/auth'
import { getFamilyCases } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import LoadState from '../../components/LoadState.vue'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const children = ref([])
const familyCases = ref([])

function avatarColor() { return '#253D61' }

function guardRole() {
  if (!auth.isLoggedIn) { uni.showToast({ title: '请先登录', icon: 'none' }); uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'parent') { uni.showToast({ title: '当前角色无法访问', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false }
  return true
}
onShow(() => { if (guardRole()) load() })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [kids, cases] = await Promise.all([
      getMyChildren(),
      getFamilyCases(),
    ])
    children.value = Array.isArray(kids) ? kids : []
    familyCases.value = Array.isArray(cases) ? cases : []
  } catch (_) { error.value = '暂时无法读取孩子档案，请检查网络后重试。' } finally { loading.value = false }
}

function openCases(child) {
  const matched = familyCases.value.find((c) => c.student_id === child.student_id)
  if (matched) return uni.navigateTo({ url: `/subParent/caseDetail/index?id=${matched.id}` })
  uni.showToast({ title: '该孩子暂无已发布档案', icon: 'none' })
}
function openCase(id) { uni.navigateTo({ url: `/subParent/caseDetail/index?id=${id}` }) }
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 18rpx; }
.head { margin-bottom: 4rpx; }
.h1 { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; line-height: 1.6; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.list { display: flex; flex-direction: column; gap: 14rpx; }
.child-card {
  display: flex; gap: 18rpx; align-items: center;
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.avatar {
  width: 72rpx; height: 72rpx; border-radius: 10rpx;
  display: flex; align-items: center; justify-content: center;
}
.avatar-text { color: #fff; font-size: 28rpx; font-weight: 700; }
.child-info { flex: 1; }
.title-row { display: flex; gap: 10rpx; align-items: center; flex-wrap: wrap; }
.name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.summary { font-size: 24rpx; color: #526177; display: block; margin-top: 6rpx; line-height: 1.5; }
.meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.arrow { font-size: 36rpx; color: var(--mp-muted); }

.card {
  background: #fff; border-radius: 10rpx; padding: 22rpx;
  border: 1rpx solid var(--mp-line);
}
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-bottom: 12rpx; }
.case-row { display: flex; justify-content: space-between; align-items: center; padding: 14rpx 0; }
.case-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.case-name { font-size: 26rpx; color: var(--mp-body); }
.empty-tip { text-align: center; font-size: 24rpx; color: var(--mp-muted); padding: 16rpx; }

.page { padding: 28rpx 32rpx calc(40rpx + env(safe-area-inset-bottom)); gap: 24rpx; }.h1 { font-size: 38rpx; font-weight: 600; }.p { font-size: 25rpx; margin-top: 12rpx; }
.child-card { align-items: flex-start; border: 0; border-radius: 16rpx; padding: 28rpx; }.avatar { flex-shrink: 0; width: 68rpx; height: 68rpx; }.name { font-size: 31rpx; }.summary { font-size: 26rpx; margin-top: 16rpx; line-height: 1.8; }.meta { margin-top: 16rpx; line-height: 1.7; }
.card { border: 0; border-radius: 16rpx; padding: 28rpx; }.card-title { font-size: 28rpx; }.case-row { padding: 24rpx 0; gap: 18rpx; flex-wrap: wrap; }.case-name { font-size: 28rpx; }
</style>
