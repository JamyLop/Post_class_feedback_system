<template>
  <view v-if="total || error" class="assignment-reminders">
    <button class="reminder-toggle" :aria-expanded="expanded" @click="expanded = !expanded">
      <view class="reminder-heading"><text class="reminder-title">初评待填</text><text class="reminder-count">{{ error ? '!' : total }}</text></view>
      <text class="toggle-label">{{ expanded ? '收起' : '查看' }} {{ expanded ? '⌃' : '›' }}</text>
    </button>
    <view v-if="expanded" class="reminder-panel">
      <view class="panel-heading"><text>待填入学初评</text><button class="refresh" :disabled="loading" @click="refresh()">刷新</button></view>
      <text v-if="error" class="reminder-error">提醒加载失败，请刷新重试。</text>
      <template v-else>
        <button v-for="item in items" :key="item.plan_id" class="reminder-task" @click="openPlan(item)">
          <view class="reminder-copy"><text class="student-name">{{ item.student_name }}</text><text class="reminder-meta">{{ item.class_name }}</text></view>
          <text class="task-subject">{{ item.subject }}</text><text class="task-action">去填写 ›</text>
        </button>
        <button v-if="items.length < total" class="more" :disabled="loading" @click="refresh(true)">查看更多（{{ total - items.length }}）</button>
      </template>
    </view>
  </view>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { getSubjectPlanReminders } from '../api/studentCases'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
const total = ref(0)
const items = ref([])
const loading = ref(false)
const error = ref(false)
const expanded = ref(false)
let disposed = false
let timer
async function refresh(more = false) {
  if (loading.value || disposed) return
  if (!auth.isLoggedIn || !['teacher', 'subject_teacher'].includes(auth.role)) {
    total.value = 0
    items.value = []
    error.value = false
    return
  }
  const userId = auth.user?.id
  loading.value = true
  try {
    const data = await getSubjectPlanReminders({ offset: more ? items.value.length : 0, limit: 3 })
    if (disposed || userId !== auth.user?.id || !auth.isLoggedIn) return
    total.value = data.total
    items.value = more ? [...new Map([...items.value, ...data.items].map(item => [item.plan_id, item])).values()] : data.items
    error.value = false
  } catch { if (!disposed && userId === auth.user?.id && auth.isLoggedIn) error.value = true }
  finally { loading.value = false }
}
function openPlan(item) {
  expanded.value = false
  uni.navigateTo({ url: `/subTeacher/caseEdit/index?caseId=${item.case_id}&tab=subjects&subject=${encodeURIComponent(item.subject)}` })
}
function pause() { clearInterval(timer) }
function resume() { pause(); refresh(); timer = setInterval(() => refresh(), 30000) }
onMounted(resume)
onUnmounted(() => { disposed = true; pause() })
defineExpose({ refresh, resume, pause })
</script>

<style scoped>
.assignment-reminders { margin-bottom: 20rpx; border: 1rpx solid var(--mp-line); border-radius: 12rpx; background: #fff; color: var(--mp-ink); }
.reminder-toggle { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; margin: 0; padding: 22rpx 24rpx; border-radius: 12rpx; background: transparent; text-align: left; line-height: 1.5; }
.reminder-heading { display: flex; align-items: center; gap: 14rpx; }
.reminder-title { font-size: 27rpx; font-weight: 500; color: var(--mp-ink); }
.reminder-count { min-width: 32rpx; padding: 0 8rpx; border-radius: 6rpx; background: var(--mp-primary); color: #fff; text-align: center; font-size: 22rpx; line-height: 34rpx; }
.toggle-label, .refresh, .more { color: var(--mp-body); font-size: 24rpx; }
.toggle-label { flex-shrink: 0; }
.reminder-panel { padding: 0 24rpx 8rpx; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; padding: 14rpx 0 8rpx; border-top: 1rpx solid var(--mp-line); color: var(--mp-body); font-size: 23rpx; }
.refresh, .more { margin: 0; padding: 8rpx 0; background: transparent; line-height: 1.6; }
.reminder-task { display: flex; align-items: center; gap: 20rpx; width: 100%; padding: 20rpx 0; border-radius: 0; background: transparent; text-align: left; line-height: 1.5; }
.reminder-task + .reminder-task { border-top: 1rpx solid var(--mp-line); }
.reminder-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 6rpx; overflow-wrap: anywhere; }
.student-name { color: var(--mp-ink); font-size: 28rpx; font-weight: 600; }
.reminder-meta { color: var(--mp-body); font-size: 23rpx; }
.task-subject { flex-shrink: 0; color: var(--mp-body); font-size: 24rpx; }
.task-action { flex-shrink: 0; color: var(--mp-primary); font-size: 24rpx; }
.reminder-error { display: block; padding: 20rpx 0; color: var(--mp-body); font-size: 24rpx; }
</style>
