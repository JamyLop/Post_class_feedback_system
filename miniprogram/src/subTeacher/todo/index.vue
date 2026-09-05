<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">{{ headTitle }}</text>
      <text class="p">{{ headDesc }}</text>
    </view>

    <LoadState :loading="loading" :error="error" @retry="refresh" />
    <template v-if="!loading && !error">
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
        <view class="list-heading"><text class="card-title">待跟进档案</text><text class="list-link" @click="goCaseList">全部档案 ›</text></view>
        <view v-for="(c, idx) in pendingCases" :key="c.id" class="case-row" :class="{ 'has-border': idx > 0 }" @click="openCase(c.id)">
          <view class="case-info">
            <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
            <text class="case-meta">{{ c.class_name }} · 第{{ c.version }}版 · {{ (c.updated_at||'').slice(0,10) }}</text>
          </view>
          <CaseStatusTag :status="c.status" />
        </view>
      </view>

      <text class="tools-title">常用操作</text>
      <view class="nav-grid">
        <view v-for="n in navItems" :key="n.title" class="nav-card" hover-class="tap-active" @click="n.action">

          <view class="nav-copy"><text class="nav-title">{{ n.title }}</text><text class="nav-desc">{{ n.desc }}</text></view><text class="nav-arrow">›</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'
import LoadState from '../../components/LoadState.vue'
import CaseStatusTag from '../../components/CaseStatusTag.vue'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
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
  if (!['teacher', 'deyu_director', 'admin', 'consultant', 'subject_teacher'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [p, list] = await Promise.all([
      getCaseProgress(),
      listStudentCases(),
    ])
    progress.value = p || {}
    const arr = Array.isArray(list) ? list : []
    const priority = { revision_required:0, pending_confirmation:1, draft:2, pending_review:3 }
    pendingCases.value = arr
      .filter(c => ['revision_required','pending_confirmation','draft','pending_review'].includes(c.status))
      .sort((a,b) => (priority[a.status]??9)-(priority[b.status]??9) || new Date(b.updated_at)-new Date(a.updated_at))
      .slice(0,10)
  } catch (_) { error.value = '暂时无法读取工作进展，请检查网络后重试。' } finally { loading.value = false }
}

function openCase(id) { uni.navigateTo({ url: `/subTeacher/caseDetail/index?id=${id}` }) }
function goCaseList() { uni.navigateTo({ url: '/subTeacher/caseList/index' }) }
function goCheckin() { uni.navigateTo({ url: '/subTeacher/caseList/index?action=checkin' }) }
function goReview() { uni.navigateTo({ url: '/subTeacher/reviewCreate/index' }) }
function goDeyuReview() { uni.navigateTo({ url: '/subTeacher/deyuReview/index' }) }
function goAdminStats() { uni.navigateTo({ url: '/subTeacher/adminStats/index' }) }
function goWeeklyScores() { uni.navigateTo({ url: '/subTeacher/weeklyScores/index' }) }
function goMonthlyReports() { uni.navigateTo({ url: '/subTeacher/monthlyReports/index' }) }
function goClassManager() { uni.navigateTo({ url: '/subTeacher/classManager/index' }) }

const navItems = computed(() => {
  const items = []
  if (auth.role === 'teacher') {
    items.push({ title: '班级档案', desc: '按班级筛选', action: goCaseList })
    items.push({ title: '快速打卡', desc: '先选档案，再记录执行', action: goCheckin })
    items.push({ title: '提交督查', desc: '提交档案督查', action: goReview })
    items.push({ title: '周测成绩', desc: '录入与查看', action: goWeeklyScores })
    items.push({ title: '月度评定', desc: '审阅与发布评定', action: goMonthlyReports })
    items.push({ title: '班级管理', desc: '管理班级学生', action: goClassManager })
  } else if (auth.role === 'deyu_director') {
    items.push({ title: '德育审查', desc: '审查待审方案', action: goDeyuReview })
    items.push({ title: '全部档案', desc: '全局档案查看', action: goCaseList })
    items.push({ title: '档案进展', desc: '查看任务与督查记录', action: goCaseList })
  } else if (auth.role === 'admin') {
    items.push({ title: '系统管理', desc: '统计与配置', action: goAdminStats })
    items.push({ title: '全部档案', desc: '全局档案查看', action: goCaseList })
    items.push({ title: '班级管理', desc: '管理班级与学生', action: goClassManager })
  } else if (auth.role === 'consultant') {
    items.push({ title: '关联学生', desc: '查看负责学生档案', action: () => uni.reLaunch({ url: '/subConsultant/caseList/index' }) })
  } else if (auth.role === 'subject_teacher') {
    items.push({ title: '学生档案', desc: '查看所带班级档案', action: goCaseList })
  }
  return items
})

const headTitle = computed(() => ({
  teacher: '班级工作台',
  deyu_director: '德育审查工作台',
  admin: '系统管理总览',
  consultant: '咨询老师工作台',
  subject_teacher: '任课老师工作台',
}[auth.role] || '工作台'))

const headDesc = computed(() => ({
  teacher: '聚合逾期任务与待复盘档案',
  deyu_director: '审查班主任提交的方案',
  admin: '系统统计与用户管理',
  consultant: '查看关联学生档案',
  subject_teacher: '查看所带班级学生档案',
}[auth.role] || ''))

onShow(() => { if (guardRole()) refresh() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.stats { display: flex; gap: 14rpx; }
.stat-card {
  flex: 1;
  background: #fff;
  border-radius: 10rpx;
  padding: 22rpx 16rpx;
  text-align: center;
  border: 1rpx solid var(--mp-line);
}
.stat-card.stat-warn { background: #FFF8E8; }
.stat-num { font-size: 36rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.num-warn { color: #865C1E; }
.stat-label { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }

.card {
  background: #fff;
  border-radius: 10rpx;
  padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-bottom: 14rpx; }

.chips { display: flex; flex-wrap: wrap; gap: 10rpx; }
.chip {
  display: flex; align-items: center; gap: 6rpx;
  font-size: 24rpx;
  padding: 8rpx 16rpx;
  background: #F3F5F8;
  border-radius: 20rpx;
  color: #526177;
}
.chip.is-revision_required { background: #FAECE9; color: #A33E39; }
.chip.is-pending_confirmation, .chip.is-pending_review { background: #FBF1DF; color: #865C1E; }
.chip.is-executing { background: #EAF3EE; color: #286349; }
.chip-num { font-weight: 700; }

.case-row { padding: 16rpx 0; }
.case-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.case-info { flex: 1; }
.case-name { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.case-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }

.nav-grid { display: flex; flex-wrap: wrap; gap: 14rpx; }
.nav-card {
  width: calc(33.33% - 10rpx);
  background: #fff;
  border-radius: 10rpx;
  padding: 22rpx 12rpx;
  text-align: center;
  border: 1rpx solid var(--mp-line);
  box-sizing: border-box;
}
.nav-icon { font-size: 36rpx; display: block; margin-bottom: 8rpx; }
.nav-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.nav-desc { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }

.head { padding: 8rpx 0 12rpx; }.h1 { font-size: 38rpx; }.p { line-height: 1.7; margin-top: 12rpx; }
.stats { gap: 0; border: 1rpx solid var(--mp-line); background: white; border-radius: 16rpx; padding: 24rpx 0; }
.stat-card { border: 0; border-radius: 0; padding: 0 12rpx; background: transparent; }.stat-card + .stat-card { border-left: 1rpx solid var(--mp-line); }.stat-card.stat-warn { background: transparent; }.stat-num { font-size: 40rpx; }.stat-label { margin-top: 8rpx; }
.card { border: 0; border-radius: 16rpx; padding: 28rpx; }.card-title { font-size: 28rpx; color: var(--mp-ink); }.chips { gap: 14rpx; }.chip { font-size: 24rpx; border-radius: 6rpx; }
.case-row { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; padding: 24rpx 0; }.case-name { font-size: 29rpx; }.case-meta { font-size: 24rpx; line-height: 1.7; }.list-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12rpx; }.list-link { font-size: 24rpx; color: var(--mp-primary); }
.tools-title { font-size: 28rpx; font-weight: 600; margin-top: 12rpx; }.nav-grid { display: flex; flex-direction: column; gap: 0; background: white; padding: 0 28rpx; border-radius: 16rpx; }.nav-card { width: 100%; display: flex; align-items: center; text-align: left; border: 0; border-radius: 0; padding: 24rpx 0; background: transparent; }.nav-card + .nav-card { border-top: 1rpx solid var(--mp-line); }.nav-copy { flex: 1; }.nav-title { font-size: 28rpx; }.nav-desc { font-size: 24rpx; margin-top: 8rpx; }.nav-arrow { color: var(--mp-muted); font-size: 32rpx; }
</style>
