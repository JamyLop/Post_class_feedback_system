<template>
  <section v-if="total || error" class="assignment-reminders" aria-label="入学初评填写提醒">
    <div class="reminder-heading">
      <strong>入学初评待填写<span v-if="total"> · {{ total }} 科</span></strong>
      <el-button link :loading="loading" @click="refresh()">刷新提醒</el-button>
    </div>
    <p v-if="error" role="status">提醒读取失败，请刷新重试。</p>
    <template v-else>
      <p>已分配给您，请填写并保存对应科目。</p>
      <div v-for="item in items" :key="item.plan_id" class="reminder-row">
        <span><strong>{{ item.student_name }}</strong> · {{ item.class_name }} · {{ item.subject }}</span>
        <el-button type="primary" plain size="small" @click="openPlan(item)">填写{{ item.subject }}初评</el-button>
      </div>
      <el-button v-if="items.length < total" link :loading="loading" @click="refresh(true)">查看更多待填写科目（{{ total - items.length }}）</el-button>
    </template>
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
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

<style scoped>
.assignment-reminders { padding: 16px; margin-bottom: 20px; border: 1px solid #d9b86c; border-radius: 8px; background: #fff8e8; color: #654710; }
.reminder-heading, .reminder-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.reminder-heading strong { font-size: 16px; }
p { margin: 4px 0 12px; font-size: 14px; }
.reminder-row { padding: 10px 0; border-top: 1px solid #e8d8b6; font-size: 14px; }
.reminder-row span { min-width: 0; overflow-wrap: anywhere; }
.reminder-row .el-button { flex-shrink: 0; }
@media (max-width: 540px) { .reminder-row { align-items: flex-start; flex-direction: column; } }
</style>
