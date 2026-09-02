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
        <view class="stat warn"><text class="num">{{ progress.overdue_tasks || 0 }}</text><text class="label">逾期任务</text></view>
        <view class="stat warn"><text class="num">{{ progress.long_unreviewed || 0 }}</text><text class="label">长期未复盘</text></view>
      </view>

      <view class="section">
        <view class="section-head">
          <text class="section-title">状态分布</text>
        </view>
        <view class="chips">
          <view v-for="(v,k) in statusCounts" :key="k" class="chip" :class="`is-${k}`">
            <text class="chip-label">{{ statusLabel(k) }}</text>
            <text class="chip-num">{{ v }}</text>
          </view>
        </view>
      </view>

      <view v-if="pendingCases.length" class="section">
        <text class="section-title">需关注（最多10条）</text>
        <view v-for="c in pendingCases" :key="c.id" class="case-row" @click="openCase(c.id)">
          <view class="case-copy">
            <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }} · {{ c.class_name || '' }}</text>
            <text class="case-meta">第{{ c.version }}版 · {{ statusLabel(c.status) }} · 更新 {{ (c.updated_at||'').slice(0,10) }}</text>
          </view>
          <CaseStatusTag :status="c.status" />
        </view>
      </view>

      <view class="nav-grid">
        <view class="nav-card" @click="goCaseList">
          <text class="nav-title">全部档案</text>
          <text class="nav-desc">按班级/状态筛选查看</text>
        </view>
        <view class="nav-card" @click="goCheckin">
          <text class="nav-title">快速打卡</text>
          <text class="nav-desc">选择任务完成打卡</text>
        </view>
        <view class="nav-card" @click="goReview">
          <text class="nav-title">提交督查</text>
          <text class="nav-desc">选择档案提交督查意见</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'

const auth = useAuthStore()
const loading = ref(false)
const progress = ref({})
const pendingCases = ref([])

const statusCounts = computed(() => {
  const keys = ['draft','pending_confirmation','revision_required','executing','pending_review','adjusted','archived']
  const out = {}
  keys.forEach(k => { if (progress.value[k] !== undefined) out[k] = progress.value[k] })
  return out
})
function statusLabel(k) {
  return { draft:'草稿', pending_confirmation:'待德育审查', revision_required:'待整改', executing:'执行中', pending_review:'待复盘', adjusted:'已调整', archived:'已归档' }[k] || k
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['teacher', 'deyu_director', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function refresh() {
  loading.value = true
  try {
    const [p, list] = await Promise.all([
      getCaseProgress().catch(() => ({})),
      listStudentCases().catch(() => []),
    ])
    progress.value = p || {}
    const arr = Array.isArray(list) ? list : []
    const priority = { revision_required:0, pending_confirmation:1, draft:2, pending_review:3 }
    pendingCases.value = arr
      .filter(c => ['revision_required','pending_confirmation','draft','pending_review'].includes(c.status))
      .sort((a,b) => (priority[a.status]??9)-(priority[b.status]??9) || new Date(b.updated_at)-new Date(a.updated_at))
      .slice(0,10)
  } finally { loading.value = false }
}

function openCase(id) { uni.navigateTo({ url: `/subTeacher/caseDetail/index?id=${id}` }) }
function goCaseList() { uni.navigateTo({ url: '/subTeacher/caseList/index' }) }
function goCheckin() { uni.navigateTo({ url: '/subTeacher/checkin/index' }) }
function goReview() { uni.navigateTo({ url: '/subTeacher/reviewCreate/index' }) }

onShow(() => { if (guardRole()) refresh() })
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.p { font-size:24rpx; color:#64748b; display:block; margin-top:6rpx; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
.stats { display:flex; gap:12rpx; }
.stat { flex:1; background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:20rpx; text-align:center; }
.stat.warn .num { color:#d97706; }
.num { font-size:32rpx; font-weight:700; color:#0f172a; display:block; }
.label { font-size:20rpx; color:#64748b; display:block; margin-top:4rpx; }
.section { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:20rpx; }
.section-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12rpx; }
.section-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; }
.chips { display:flex; flex-wrap:wrap; gap:10rpx; }
.chip { display:flex; gap:8rpx; align-items:center; font-size:20rpx; padding:8rpx 14rpx; background:#f8fafc; border:1rpx solid #e2e8f0; border-radius:999rpx; color:#334155; }
.chip.is-revision_required { background:#fff7ed; border-color:#fdba74; color:#9a3412; }
.chip.is-pending_confirmation { background:#fef3c7; border-color:#fde68a; color:#92400e; }
.chip-label { font-weight:500; }
.chip-num { font-weight:700; }
.case-row { display:flex; justify-content:space-between; align-items:center; padding:14rpx 0; border-top:1rpx solid #f1f5f9; gap:12rpx; }
.case-row:first-of-type { border-top:none; }
.case-copy { flex:1; }
.case-name { font-size:24rpx; font-weight:600; color:#0f172a; display:block; }
.case-meta { font-size:20rpx; color:#94a3b8; display:block; margin-top:4rpx; }
.nav-grid { display:flex; gap:12rpx; }
.nav-card { flex:1; background:#fff; border:1rpx solid #e2e8f0; border-radius:12rpx; padding:18rpx; text-align:center; }
.nav-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; }
.nav-desc { font-size:20rpx; color:#64748b; display:block; margin-top:4rpx; }
</style>
