<template>
  <section class="page">
    <div class="page-header"><span class="page-title">我的周测成绩</span></div>
    <div class="filter-bar">
      <el-select v-model="subject" placeholder="全部学科" clearable style="width: 160px" @change="load">
        <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button @click="load">刷新</el-button>
    </div>
    <div v-if="trend.length" ref="chartRef" style="height: 280px; margin: 16px 0; background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 12px"></div>
    <el-table :data="rows" v-loading="loading" empty-text="暂无周测成绩">
      <el-table-column prop="subject" label="学科" width="100" />
      <el-table-column prop="exam_date" label="日期" width="120" />
      <el-table-column prop="exam_name" label="周次" min-width="140" />
      <el-table-column label="分数" width="120"><template #default="{ row }">{{ row.score }} / {{ row.max_score }}</template></el-table-column>
      <el-table-column prop="rank_in_class" label="排名" width="90"><template #default="{ row }">{{ row.rank_in_class || '-' }}</template></el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
    </el-table>
  </section>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { listWeeklyScores, getWeeklyTrend } from '../../api/weeklyScores'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const subjects = ['语文','数学','英语','物理','化学','生物','政治','历史','地理']
const subject = ref('')
const rows = ref([])
const trend = ref([])
const loading = ref(false)
const chartRef = ref(null)
let chart = null

async function load() {
  loading.value = true
  try {
    rows.value = await listWeeklyScores({ student_id: auth.user?.id, subject: subject.value || undefined })
    trend.value = await getWeeklyTrend({ student_id: auth.user?.id, subject: subject.value || undefined })
    await nextTick()
    render()
  } finally { loading.value = false }
}

function render() {
  if (!chartRef.value || !trend.value.length) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: trend.value.map(d => d.exam_date) },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, data: trend.value.map(d => d.score), areaStyle: {} }],
    grid: { left: 40, right: 20, top: 20, bottom: 30 }
  })
}

watch(subject, load)
onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.page-header { margin-bottom: 12px; }
.page-title { font-weight: 700; font-size: 18px; }
.filter-bar { display: flex; gap: 10px; align-items: center; }
</style>
