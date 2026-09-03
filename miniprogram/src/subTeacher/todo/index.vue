<template>
  <view class="page">
    <view class="head">
      <text class="h1">{{ headTitle }}</text>
      <text class="p">{{ headDesc }}</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view class="stats">
        <view class="stat-card">
          <text class="stat-num">{{ progress.total || 0 }}</text>
          <text class="stat-label">总档案</text>
        </view>
        <view class="stat-card stat-warn">
          <text class="stat-num num-warn">{{ progress.overdue_tasks || 0 }}</text>
          <text class="stat-label">逾期任务</text>
        </view>
        <view class="stat-card stat-warn">
          <text class="stat-num num-warn">{{ progress.long_unreviewed || 0 }}</text>
          <text class="stat-label">长期未复盘</text>
        </view>
      </view>

      <view class="card">
        <text class="card-title">状态分布</text>
        <view class="chips">
          <view v-for="(v,k) in statusCounts" :key="k" class="chip" :class="`is-${k}`">
            <text class="chip-num">{{ v }}</text>
            <text class="chip-label">{{ statusLabel(k) }}</text>
          </view>
        </view>
      </view>

      <view v-if="pendingCases.length" class="card">
        <text class="card-title">需关注</text>
        <view v-for="(c, idx) in pendingCases" :key="c.id" class="case-row" :class="{ 'has-border': idx > 0 }" @click="openCase(c.id)">
          <view class="case-info">
            <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
            <text class="case-meta">{{ c.class_name }} · 第{{ c.version }}版 · {{ (c.updated_at||'').slice(0,10) }}</text>
          </view>
          <CaseStatusTag :status="c.status" />
        </view>
      </view>

      <view class="nav-grid">
        <view v-for="n in navItems" :key="n.title" class="nav-card" @click="n.action">
          <text class="nav-icon">{{ n.icon }}</text>
          <text class="nav-title">{{ n.title }}</text>
          <text class="nav-desc">{{ n.desc }}</text>
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
  return { draft:'草稿', pending_confirmation:'待审查', revision_required:'待整改', executing:'执行中', pending_review:'待复盘', adjusted:'已调整', archived:'已归档' }[k] || k
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
function goDeyuReview() { uni.navigateTo({ url: '/subTeacher/deyuReview/index' }) }
function goAdminStats() { uni.navigateTo({ url: '/subTeacher/adminStats/index' }) }
function goWeeklyScores() { uni.navigateTo({ url: '/subTeacher/weeklyScores/index' }) }
function goMonthlyReports() { uni.navigateTo({ url: '/subTeacher/monthlyReports/index' }) }
function goClassManager() { uni.navigateTo({ url: '/subTeacher/classManager/index' }) }

const navItems = computed(() => {
  const items = []
  if (auth.role === 'teacher') {
    items.push({ title: '全部档案', desc: '按班级筛选', icon: '📚', action: goCaseList })
    items.push({ title: '快速打卡', desc: '选择任务打卡', icon: '✅', action: goCheckin })
    items.push({ title: '提交督查', desc: '提交档案督查', icon: '📤', action: goReview })
    items.push({ title: '周测成绩', desc: '录入与查看', icon: '📊', action: goWeeklyScores })
    items.push({ title: '月度评价', desc: 'AI生成评价', icon: '📋', action: goMonthlyReports })
    items.push({ title: '班级管理', desc: '管理班级学生', icon: '🏫', action: goClassManager })
  } else if (auth.role === 'deyu_director') {
    items.push({ title: '德育审查', desc: '审查待审方案', icon: '🔍', action: goDeyuReview })
    items.push({ title: '全部档案', desc: '全局档案查看', icon: '📚', action: goCaseList })
    items.push({ title: '督查进度', desc: '逾期与未复盘', icon: '📊', action: goReview })
  } else if (auth.role === 'admin') {
    items.push({ title: '系统管理', desc: '统计与配置', icon: '⚙️', action: goAdminStats })
    items.push({ title: '全部档案', desc: '全局档案查看', icon: '📚', action: goCaseList })
    items.push({ title: '德育审查', desc: '审查待审方案', icon: '🔍', action: goDeyuReview })
  }
  return items
})

const headTitle = computed(() => ({
  teacher: '班级工作台',
  deyu_director: '德育审查工作台',
  admin: '系统管理总览',
}[auth.role] || '工作台'))

const headDesc = computed(() => ({
  teacher: '聚合逾期任务与待复盘档案',
  deyu_director: '审查班主任提交的方案',
  admin: '系统统计与用户管理',
}[auth.role] || ''))

onShow(() => { if (guardRole()) refresh() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.stats { display: flex; gap: 14rpx; }
.stat-card {
  flex: 1;
  background: #fff;
  border-radius: 10rpx;
  padding: 22rpx 16rpx;
  text-align: center;
  border: 1rpx solid #E0E7E5;
}
.stat-card.stat-warn { background: #FFF8E8; }
.stat-num { font-size: 36rpx; font-weight: 700; color: #1A1636; display: block; }
.num-warn { color: #D97706; }
.stat-label { font-size: 20rpx; color: #8E8B9E; display: block; margin-top: 4rpx; }

.card {
  background: #fff;
  border-radius: 10rpx;
  padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; margin-bottom: 14rpx; }

.chips { display: flex; flex-wrap: wrap; gap: 10rpx; }
.chip {
  display: flex; align-items: center; gap: 6rpx;
  font-size: 20rpx;
  padding: 8rpx 16rpx;
  background: #F5F3EF;
  border-radius: 20rpx;
  color: #6E6B83;
}
.chip.is-revision_required { background: #F7E0D9; color: #9C4E3F; }
.chip.is-pending_confirmation, .chip.is-pending_review { background: #F8E8B8; color: #8A641C; }
.chip.is-executing { background: #E0F0E7; color: #2E7D5B; }
.chip-num { font-weight: 700; }

.case-row { padding: 16rpx 0; }
.case-row.has-border { border-top: 2rpx solid #F0EFFC; }
.case-info { flex: 1; }
.case-name { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.case-meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 4rpx; }

.nav-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.nav-card {
  width: calc(33.33% - 10rpx);
  background: #fff;
  border-radius: 10rpx;
  padding: 22rpx 12rpx;
  text-align: center;
  border: 1rpx solid #E0E7E5;
  box-sizing: border-box;
}
.nav-icon { font-size: 36rpx; display: block; margin-bottom: 8rpx; }
.nav-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.nav-desc { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
</style>
