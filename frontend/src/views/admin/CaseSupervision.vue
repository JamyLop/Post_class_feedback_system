<template>
  <section class="page">
    <div><p class="eyebrow">校级督查</p><h1>高三督查驾驶舱</h1><p class="muted">关注未确认、任务逾期、长期未督查和待复盘学生，不替代教师专业判断。</p></div>
    <div class="metrics">
      <div v-for="item in cards" :key="item.key" class="metric" :class="item.tone"><span>{{ item.label }}</span><strong>{{ progress[item.key] || 0 }}</strong></div>
    </div>
    <el-card shadow="never">
      <template #header><div class="card-head"><b>高三学生总案状态</b><el-button @click="load">刷新</el-button></div></template>
      <el-table v-loading="loading" :data="rows" empty-text="尚无高三试点数据">
        <el-table-column prop="student_name" label="学生" /><el-table-column prop="class_name" label="班级" /><el-table-column prop="admission_target" label="升学目标" min-width="200" /><el-table-column prop="status" label="状态" /><el-table-column prop="version" label="版本" />
      </el-table>
    </el-card>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getCaseProgress, listStudentCases } from '../../api/studentCases'
const loading = ref(false), rows = ref([]), progress = ref({})
const cards = computed(() => [
  { key: 'total', label: '高三总案', tone: '' }, { key: 'pending_confirmation', label: '待确认', tone: 'amber' },
  { key: 'overdue_tasks', label: '任务逾期', tone: 'red' }, { key: 'long_unreviewed', label: '长期未督查', tone: 'red' },
  { key: 'pending_review', label: '待复盘', tone: 'blue' }, { key: 'executing', label: '执行中', tone: 'green' },
])
async function load() { loading.value = true; try { ;[progress.value, rows.value] = await Promise.all([getCaseProgress(), listStudentCases()]) } finally { loading.value = false } }
onMounted(load)
</script>

<style scoped>
.page { display: grid; gap: 20px; }.eyebrow { margin: 0; color: #7c3aed; font-weight: 700; }.page h1 { margin: 5px 0 8px; font-size: 28px; }.muted { margin: 0; color: #64748b; }
.metrics { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }.metric { padding: 18px; background: #fff; border: 1px solid #e2e8f0; border-top: 3px solid #94a3b8; border-radius: 10px; }.metric span,.metric strong { display: block; }.metric span { color: #64748b; font-size: 13px; }.metric strong { margin-top: 8px; font-size: 28px; }.metric.red { border-top-color: #ef4444; }.metric.amber { border-top-color: #f59e0b; }.metric.blue { border-top-color: #3b82f6; }.metric.green { border-top-color: #10b981; }.card-head { display: flex; justify-content: space-between; align-items: center; }
@media (max-width: 1100px) { .metrics { grid-template-columns: repeat(3, 1fr); } }
</style>
