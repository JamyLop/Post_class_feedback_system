<template>
  <section class="family-page">
    <header><span class="eyebrow">家校共育 · 学业发展档案</span><h1>孩子的一生一案</h1><p>这里展示班主任已经确认并发布的学业目标、学科方案、任务安排和执行记录。</p></header>
    <el-skeleton v-if="loading" :rows="5" animated />
    <div v-else-if="cases.length" class="case-list">
      <article v-for="item in cases" :key="item.id" class="case-card" @click="$router.push(`/parent/children/${item.id}`)">
        <div class="student-mark">{{ item.student_name?.slice(0, 1) }}</div>
        <div class="case-copy"><div><h2>{{ item.student_name }}</h2><span>{{ item.class_name }}</span></div><p>{{ item.current_summary || '班主任正在持续记录学业发展情况。' }}</p><small>第 {{ item.version }} 版 · {{ statusLabel(item.status) }}</small></div>
        <el-button type="primary" plain>查看完整档案</el-button>
      </article>
    </div>
    <el-empty v-else description="班主任尚未发布可查看的学生档案" />
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getFamilyCases } from '../../api/studentCases'

const cases = ref([])
const loading = ref(false)
const statusLabel = (status) => ({ executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }[status] || status)
async function load() { loading.value = true; try { cases.value = await getFamilyCases() } finally { loading.value = false } }
onMounted(load)
</script>

<style scoped>
.family-page { width: min(1120px, calc(100% - 48px)); margin: 0 auto; padding: 56px 0 80px; }.family-page header { margin-bottom: 32px; }.eyebrow { color: var(--brand-strong); font-size: 13px; font-weight: 700; }.family-page h1 { margin: 9px 0 10px; font-size: 34px; letter-spacing: -.03em; }.family-page header p { margin: 0; color: var(--ink-secondary); line-height: 1.8; }.case-list { display: grid; gap: 16px; }.case-card { display: grid; grid-template-columns: 58px minmax(0, 1fr) auto; align-items: center; gap: 20px; padding: 24px 26px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-md); box-shadow: var(--shadow-raised); cursor: pointer; }.student-mark { display: grid; place-items: center; width: 58px; height: 58px; color: var(--brand-strong); background: var(--brand-soft); border-radius: 16px; font-size: 22px; font-weight: 800; }.case-copy > div { display: flex; align-items: baseline; gap: 12px; }.case-copy h2 { margin: 0; font-size: 20px; }.case-copy span, .case-copy small { color: var(--ink-muted); font-size: 12px; }.case-copy p { margin: 7px 0; color: var(--ink-secondary); line-height: 1.65; }@media (max-width: 680px) { .case-card { grid-template-columns: 48px 1fr; }.case-card .el-button { grid-column: 1 / -1; }.student-mark { width: 48px; height: 48px; } }
</style>
