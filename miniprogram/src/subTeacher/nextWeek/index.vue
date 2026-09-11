<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">下周待建周任务</text>
      <text class="p">{{ weekRangeText }}尚无生效中周计划任务覆盖的档案，请提前建好下周周任务</text>
    </view>

    <view class="hint-card">
      <text class="hint-text">口径：下周一至下周日范围内，没有周计划任务覆盖即列出（已归档除外）。去建任务后在档案内按周计划新建，需填写每周执行次数。</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <EmptyState v-else-if="!missing.length" title="下周周任务均已建好" desc="暂无需要提前建任务的档案" />
    <view v-else class="case-list">
      <view v-for="(m, idx) in missing" :key="m.case_id" class="case-card" :class="{ 'has-border': idx > 0 }">
        <view class="case-info" @click="goCase(m.case_id)">
          <view class="case-head">
            <text class="case-name">{{ m.student_name || `学生 #${m.student_id}` }}</text>
            <text class="case-status">{{ caseStatusText(m.case_status) }}</text>
          </view>
          <text class="case-meta">{{ m.class_name || '' }} · 第{{ m.version || 1 }}版 · 生效中周任务{{ m.active_weekly_count || 0 }}个</text>
        </view>
        <view class="class-actions">
          <text class="action-btn" @click="goCase(m.case_id)">去建任务 ›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getTaskReminders } from '../../api/studentCases'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const missing = ref([])
const weekStart = ref('')
const weekEnd = ref('')

const weekRangeText = computed(() => (weekStart.value && weekEnd.value ? `下周（${weekStart.value} 至 ${weekEnd.value}）` : '下周'))

function caseStatusText(s) {
  return { draft: '草稿', pending_confirmation: '待审查', revision_required: '待整改', executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }[s] || s || '-'
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  // 与 Web 任务提醒中心一致：班主任及督查角色可看
  if (!['teacher', 'admin', 'deyu_director'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadData() {
  loading.value = true
  try {
    const data = await getTaskReminders()
    missing.value = data.next_week_missing || []
    weekStart.value = data.next_week_starts_on || ''
    weekEnd.value = data.next_week_ends_on || ''
  } catch (e) {
    missing.value = []
  } finally {
    loading.value = false
  }
}

function goCase(caseId) {
  uni.navigateTo({ url: `/subTeacher/caseDetail/index?id=${caseId}` })
}

onMounted(() => { if (guardRole()) loadData() })
onShow(() => { if (auth.isLoggedIn && ['teacher', 'admin', 'deyu_director'].includes(auth.role)) loadData() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; line-height: 1.6; }

.hint-card {
  background: #FFF8E8; border-radius: 10rpx; padding: 18rpx;
  border: 1rpx solid #FBF1DF;
}
.hint-text { font-size: 24rpx; color: #865C1E; display: block; line-height: 1.6; }

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.case-list { display: flex; flex-direction: column; }
.case-card {
  background: #fff; border-radius: 12rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line); display: flex; align-items: center; justify-content: space-between;
}
.case-card.has-border { margin-top: 16rpx; }
.case-info { flex: 1; }
.case-head { display: flex; align-items: center; gap: 12rpx; }
.case-name { font-size: 30rpx; font-weight: 600; color: var(--mp-ink); }
.case-status {
  font-size: 22rpx; color: #865C1E; background: #FBF1DF;
  padding: 4rpx 12rpx; border-radius: 14rpx;
}
.case-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.class-actions { margin-left: 16rpx; }
.action-btn {
  font-size: 24rpx; color: #fff; font-weight: 500;
  padding: 12rpx 20rpx; background: var(--mp-primary); border-radius: 8rpx;
}
</style>
