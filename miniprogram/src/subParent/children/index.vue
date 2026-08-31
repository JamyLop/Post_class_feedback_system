<template>
  <view class="page">
    <view class="head">
      <text class="h1">孩子的一生一案</text>
      <text class="p">查看班主任与各科教师的备考目标、学科方案与阶段复盘（已发布版本）</text>
    </view>

    <view v-if="loading" class="skeleton">加载中…</view>

    <view v-else-if="children.length" class="list">
      <view v-for="child in children" :key="child.student_id" class="child-card" @click="openCases(child)">
        <view class="avatar">{{ (child.student_name || '孩').slice(0,1) }}</view>
        <view class="copy">
          <view class="title-row">
            <text class="name">{{ child.student_name }}</text>
            <text class="class-name">{{ child.class_name }}</text>
            <CaseStatusTag v-if="child.latest_case_status" :status="child.latest_case_status" />
          </view>
          <text class="summary">{{ child.latest_case_summary || '班主任正在持续记录学业发展情况' }}</text>
          <text class="meta">班级 #{{ child.class_id }} · 学期 {{ child.cycle_name || '-' }}</text>
        </view>
        <text class="arrow">›</text>
      </view>
    </view>

    <EmptyState v-else title="暂无绑定子女" desc="请联系班主任录入家长手机号（自动注册家长账号），或使用邀请码注册后绑定" />

    <!-- 已绑定但暂无可见总案的子项已在 children 列表中以空状态卡片体现；此处展示可见总案列表作为补充 -->
    <view v-if="familyCases.length" class="section">
      <text class="section-title">已发布档案列表（{{ familyCases.length }}）</text>
      <view v-for="c in familyCases" :key="c.id" class="case-row" @click="openCase(c.id)">
        <text class="case-name">{{ c.student_name }} · 第{{ c.version }}版</text>
        <CaseStatusTag :status="c.status" />
      </view>
    </view>
    <view v-else-if="!loading && children.length" class="empty-tip">
      <text>已绑定子女，但暂无已发布档案（等待班主任方案通过德育审查）</text>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getMyChildren } from '../../api/auth'
import { getFamilyCases } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const children = ref([])
const familyCases = ref([])

async function load() {
  loading.value = true
  try {
    const [kids, cases] = await Promise.all([
      getMyChildren().catch(() => []),
      getFamilyCases().catch(() => []),
    ])
    children.value = Array.isArray(kids) ? kids : []
    familyCases.value = Array.isArray(cases) ? cases : []
  } finally {
    loading.value = false
  }
}

function openCases(child) {
  // 若该子女有可见总案，直接进最新一条；否则提示
  const matched = familyCases.value.find((c) => c.student_id === child.student_id)
  if (matched) return uni.navigateTo({ url: `/subParent/caseDetail/index?id=${matched.id}` })
  uni.showToast({ title: '该孩子暂无已发布档案', icon: 'none' })
}
function openCase(id) { uni.navigateTo({ url: `/subParent/caseDetail/index?id=${id}` }) }

onMounted(load)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.head { margin-bottom:4rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.p { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; line-height:1.6; }
.skeleton { padding:40rpx; text-align:center; color:#64748b; }
.list { display:flex; flex-direction:column; gap:16rpx; }
.child-card { display:flex; gap:18rpx; align-items:center; background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:24rpx; }
.avatar { width:72rpx; height:72rpx; border-radius:12rpx; background:#eff6ff; border:1rpx solid #bfdbfe; color:#2563eb; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:28rpx; text-align:center; line-height:72rpx; }
.copy { flex:1; }
.title-row { display:flex; gap:12rpx; align-items:center; flex-wrap:wrap; }
.name { font-size:28rpx; font-weight:600; color:#0f172a; }
.class-name { font-size:22rpx; color:#64748b; }
.summary { font-size:24rpx; color:#475569; display:block; margin-top:6rpx; line-height:1.5; }
.meta { font-size:20rpx; color:#94a3b8; display:block; margin-top:4rpx; }
.arrow { font-size:36rpx; color:#cbd5e1; }
.section { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:20rpx; }
.section-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; margin-bottom:12rpx; }
.case-row { display:flex; justify-content:space-between; align-items:center; padding:16rpx 0; border-top:1rpx solid #f1f5f9; }
.case-row:first-of-type { border-top: none; }
.case-name { font-size:26rpx; color:#334155; }
.empty-tip { text-align:center; font-size:24rpx; color:#94a3b8; padding:16rpx; }
</style>
