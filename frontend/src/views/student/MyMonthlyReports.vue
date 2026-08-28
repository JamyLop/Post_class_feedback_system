<template>
  <section class="page" style="padding:16px">
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span class="page-title" style="font-weight:700;font-size:18px">我的月报</span>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-empty v-if="!rows.length" description="暂无已发布月报" />
    <el-card v-for="r in rows" :key="r.id" shadow="never" style="margin-bottom:16px">
      <template #header><div style="display:flex;justify-content:space-between"><strong>{{ r.month_label }} 月报</strong><span style="color:#909399;font-size:12px">{{ r.period_start }} ~ {{ r.period_end }}</span></div></template>
      <div style="white-space:pre-wrap;line-height:1.7">{{ r.final_content || r.ai_content }}</div>
      <div style="color:#909399;font-size:12px;margin-top:8px">发布时间：{{ r.published_at ? new Date(r.published_at).toLocaleString() : '-' }}</div>
    </el-card>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listMonthlyReports } from '../../api/monthlyReports'
import { useAuthStore } from '../../stores/auth'
const auth = useAuthStore()
const rows = ref([])
async function load() {
  rows.value = await listMonthlyReports({ student_id: auth.user?.id })
}
onMounted(load)
</script>
