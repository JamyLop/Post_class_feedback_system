<template>
  <view v-if="total || error" class="assignment-reminders">
    <view class="reminder-heading"><text class="reminder-title">入学初评待填写{{ total ? ` · ${total} 科` : '' }}</text><button class="refresh" :disabled="loading" @click="refresh()">刷新提醒</button></view>
    <text v-if="error" class="reminder-desc">提醒读取失败，请刷新重试。</text>
    <template v-else>
      <text class="reminder-desc">已分配给您，请填写并保存对应科目。</text>
      <view v-for="item in items" :key="item.plan_id" class="reminder-row">
        <view class="reminder-copy"><text class="student-name">{{ item.student_name }}</text><text class="reminder-meta">{{ item.class_name }} · {{ item.subject }}</text></view>
        <button class="fill" @click="openPlan(item)">填写{{ item.subject }}初评 ›</button>
      </view>
      <button v-if="items.length < total" class="more" :disabled="loading" @click="refresh(true)">查看更多待填写科目（{{ total - items.length }}）</button>
    </template>
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
  uni.navigateTo({ url: `/subTeacher/caseEdit/index?caseId=${item.case_id}&tab=subjects&subject=${encodeURIComponent(item.subject)}` })
}
function pause() { clearInterval(timer) }
function resume() { pause(); refresh(); timer = setInterval(() => refresh(), 30000) }
onMounted(resume)
onUnmounted(() => { disposed = true; pause() })
defineExpose({ refresh, resume, pause })
</script>

<style scoped>
.assignment-reminders { padding: 24rpx; margin-bottom: 24rpx; border: 1rpx solid #d9b86c; border-radius: 12rpx; background: #fff8e8; color: #654710; }
.reminder-heading { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; }
.reminder-title { font-size: 29rpx; font-weight: 600; }
.reminder-desc { display: block; margin: 8rpx 0 16rpx; font-size: 24rpx; line-height: 1.6; }
.refresh, .more { margin: 0; padding: 8rpx 0; background: transparent; color: #654710; font-size: 24rpx; line-height: 1.6; }
.refresh { flex-shrink: 0; }
.reminder-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12rpx; padding: 18rpx 0; border-top: 1rpx solid #e8d8b6; }
.reminder-copy { min-width: 0; flex: 1; overflow-wrap: anywhere; }
.student-name { display: block; font-size: 28rpx; font-weight: 600; }
.reminder-meta { display: block; margin-top: 4rpx; font-size: 24rpx; }
.fill { flex-shrink: 0; margin: 0; padding: 12rpx 16rpx; border: 1rpx solid var(--mp-primary); border-radius: 8rpx; color: var(--mp-primary); background: white; font-size: 24rpx; line-height: 1.6; }
</style>
