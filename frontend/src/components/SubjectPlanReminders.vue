<template>
  <div v-if="total || error" class="assignment-reminders">
    <el-popover v-model:visible="expanded" placement="bottom-end" trigger="click" role="dialog" :width="360" :show-arrow="false" popper-class="assignment-reminder-popover">
      <template #reference>
        <button class="reminder-trigger" :aria-label="error ? '初评提醒加载失败，点击查看' : `入学初评待填写，共 ${total} 科`" :aria-expanded="expanded" aria-haspopup="dialog">
          <el-icon><Bell /></el-icon><span class="trigger-label">初评待填</span><span class="reminder-count">{{ error ? '!' : total > 99 ? '99+' : total }}</span>
        </button>
      </template>
      <section class="reminder-panel" aria-label="待填入学初评">
        <div class="reminder-heading">
          <div><strong>待填入学初评</strong><span v-if="total" class="total-label">{{ total }} 项</span></div>
          <el-button text circle :icon="Refresh" :loading="loading" aria-label="刷新初评提醒" @click="refresh()" />
        </div>
        <p v-if="error" class="reminder-error" role="status">提醒加载失败，请点击右上角刷新重试。</p>
        <div v-else class="reminder-list">
          <button v-for="item in items" :key="item.plan_id" class="reminder-task" @click="openPlan(item)">
            <span class="task-copy"><strong>{{ item.student_name }}</strong><span>{{ item.class_name }}</span></span>
            <span class="task-subject">{{ item.subject }}</span>
            <span class="task-action">去填写<el-icon><ArrowRight /></el-icon></span>
          </button>
          <el-button v-if="items.length < total" text class="load-more" :loading="loading" @click="refresh(true)">查看更多（{{ total - items.length }}）</el-button>
        </div>
      </section>
    </el-popover>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { ArrowRight, Bell, Refresh } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { getSubjectPlanReminders } from '../api/studentCases'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const total = ref(0)
const items = ref([])
const loading = ref(false)
const error = ref(false)
const expanded = ref(false)
let timer
let disposed = false
async function refresh(more = false) {
  if (loading.value || disposed) return
  loading.value = true
  try {
    const data = await getSubjectPlanReminders({ offset: more ? items.value.length : 0, limit: 3 })
    if (disposed) return
    total.value = data.total
    items.value = more ? [...new Map([...items.value, ...data.items].map(item => [item.plan_id, item])).values()] : data.items
    error.value = false
  } catch { if (!disposed) error.value = true }
  finally { loading.value = false }
}
function openPlan(item) {
  expanded.value = false
  const base = auth.role === 'subject_teacher' ? '/subject/cases' : '/teacher/student-cases'
  router.push({ path: `${base}/${item.case_id}`, query: { tab: 'subjects', subject: item.subject, edit: '1' } })
}
function refreshVisible() { if (!document.hidden) refresh() }
watch(() => route.fullPath, () => refresh())
onMounted(() => {
  refresh()
  timer = window.setInterval(refreshVisible, 30000)
  window.addEventListener('focus', refreshVisible)
  window.addEventListener('subject-plan-updated', refreshVisible)
  document.addEventListener('visibilitychange', refreshVisible)
})
onUnmounted(() => {
  disposed = true
  window.clearInterval(timer)
  window.removeEventListener('focus', refreshVisible)
  window.removeEventListener('subject-plan-updated', refreshVisible)
  document.removeEventListener('visibilitychange', refreshVisible)
})
</script>

<style>
.assignment-reminder-popover.el-popover { width: min(360px, calc(100vw - 24px)) !important; padding: 0; border: 0; border-radius: 8px; box-shadow: var(--shadow-raised, 0 8px 24px rgba(23, 32, 51, 0.10)); }
</style>
<style scoped>
.assignment-reminders { display: flex; flex-shrink: 0; }
.reminder-trigger { display: inline-flex; align-items: center; gap: 7px; min-height: 34px; padding: 6px 10px; border: 0; border-radius: 6px; background: transparent; color: var(--ink-2, #445269); font: inherit; font-size: 13px; cursor: pointer; }
.reminder-trigger:hover, .reminder-trigger[aria-expanded="true"] { background: var(--brand-soft, #eaf3ff); color: var(--brand-strong, #1762d4); }
.reminder-trigger > .el-icon { font-size: 17px; }
.reminder-count { min-width: 18px; padding: 0 5px; border-radius: 4px; background: var(--brand-strong, #1762d4); color: #fff; font-size: 11px; font-weight: 600; line-height: 18px; text-align: center; }
.reminder-panel { color: var(--ink, #172033); }
.reminder-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--line, #e5eaf2); }
.reminder-heading > div { display: flex; align-items: baseline; gap: 8px; }
.reminder-heading strong { font-size: 14px; font-weight: 600; }
.total-label { color: var(--ink-2, #445269); font-size: 12px; }
.reminder-list { max-height: min(440px, 65vh); padding: 4px 8px; overflow-y: auto; }
.reminder-task { display: flex; align-items: center; gap: 12px; width: 100%; padding: 13px 8px; border: 0; border-radius: 4px; background: transparent; text-align: left; font: inherit; cursor: pointer; }
.reminder-task + .reminder-task { border-top: 1px solid var(--line, #e5eaf2); }
.reminder-task:hover { background: var(--surface-soft, #f8fafd); }
.task-copy { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 4px; }
.task-copy strong { color: var(--ink, #172033); font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.task-copy > span { color: var(--ink-2, #445269); font-size: 12px; overflow-wrap: anywhere; }
.task-subject { flex-shrink: 0; padding: 2px 6px; border-radius: 4px; background: var(--surface-soft, #f8fafd); color: var(--ink-2, #445269); font-size: 12px; }
.task-action { display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0; color: var(--brand-strong, #1762d4); font-size: 13px; }
.load-more { width: 100%; margin: 4px 0; }
.reminder-error { margin: 0; padding: 18px 16px; color: var(--ink-2, #445269); font-size: 13px; line-height: 1.6; }
.reminder-trigger:focus-visible, .reminder-task:focus-visible { outline: 2px solid var(--brand-strong, #1762d4); outline-offset: 2px; }
@media (max-width: 960px) { .trigger-label { display: none; } .reminder-trigger { padding: 6px; gap: 5px; } }
</style>
