<template>
  <view class="page">
    <view class="head">
      <text class="h1">孩子的一生一案</text>
      <text class="p">查看已发布总案、学科方案与阶段复盘</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>

    <view v-else-if="children.length" class="list">
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

    <EmptyState v-else title="暂无绑定子女" desc="请联系班主任录入家长手机号" icon="👨‍👩‍👧" />

    <view v-if="familyCases.length" class="card">
      <text class="card-title">已发布档案（{{ familyCases.length }}）</text>
      <view v-for="(c, idx) in familyCases" :key="c.id" class="case-row" :class="{ 'has-border': idx > 0 }" @click="openCase(c.id)">
        <text class="case-name">{{ c.student_name }} · 第{{ c.version }}版</text>
        <CaseStatusTag :status="c.status" />
      </view>
    </view>
    <view v-else-if="!loading && children.length" class="empty-tip">
      <text>已绑定子女，但暂无已发布档案</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getMyChildren } from '../../api/auth'
import { getFamilyCases } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const children = ref([])
const familyCases = ref([])

const colors = ['#1F4F55', '#4C7A64', '#B47D37', '#7E5C58', '#427B87']
function avatarColor(name) {
  const idx = (name || '').charCodeAt(0) % colors.length
  return colors[idx]
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.showToast({ title: '请先登录', icon: 'none' }); uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'parent') { uni.showToast({ title: '当前角色无法访问', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false }
  return true
}
onShow(() => { if (guardRole()) load() })

async function load() {
  loading.value = true
  try {
    const [kids, cases] = await Promise.all([
      getMyChildren().catch(() => []),
      getFamilyCases().catch(() => []),
    ])
    children.value = Array.isArray(kids) ? kids : []
    familyCases.value = Array.isArray(cases) ? cases : []
  } finally { loading.value = false }
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
.h1 { font-size: 32rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; line-height: 1.6; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.list { display: flex; flex-direction: column; gap: 14rpx; }
.child-card {
  display: flex; gap: 18rpx; align-items: center;
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.avatar {
  width: 72rpx; height: 72rpx; border-radius: 10rpx;
  display: flex; align-items: center; justify-content: center;
}
.avatar-text { color: #fff; font-size: 28rpx; font-weight: 700; }
.child-info { flex: 1; }
.title-row { display: flex; gap: 10rpx; align-items: center; flex-wrap: wrap; }
.name { font-size: 28rpx; font-weight: 600; color: #1A1636; }
.summary { font-size: 24rpx; color: #6E6B83; display: block; margin-top: 6rpx; line-height: 1.5; }
.meta { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
.arrow { font-size: 36rpx; color: #B8B0F6; }

.card {
  background: #fff; border-radius: 10rpx; padding: 22rpx;
  border: 1rpx solid #E0E7E5;
}
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; margin-bottom: 12rpx; }
.case-row { display: flex; justify-content: space-between; align-items: center; padding: 14rpx 0; }
.case-row.has-border { border-top: 2rpx solid #F0EFFC; }
.case-name { font-size: 26rpx; color: #4A4763; }
.empty-tip { text-align: center; font-size: 24rpx; color: #A09CB5; padding: 16rpx; }
</style>
