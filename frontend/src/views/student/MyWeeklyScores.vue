<template>
  <section class="page student-weekly-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">周测表现与学科趋势</h1>
        <p class="header-desc">查阅各科每周滚动测试分数、班级排名及学科成绩走势曲线。</p>
      </div>
      <div class="filter-bar">
        <el-select v-model="subject" placeholder="全部学科" clearable style="width: 140px" @change="load">
          <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <div v-if="trend.length" class="chart-card">
      <div class="card-head">
        <span class="dot"></span>
        <span class="title">周测分数趋势图</span>
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </div>

    <div class="table-card">
      <el-table :data="rows" v-loading="loading" empty-text="暂无周测成绩记录" style="width: 100%">
        <el-table-column prop="subject" label="学科" width="100">
          <template #default="{ row }">
            <span class="subject-badge">{{ row.subject }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="exam_date" label="考试日期" width="120" />
        <el-table-column prop="exam_name" label="测试周次" min-width="150" />
        <el-table-column label="得分" width="130">
          <template #default="{ row }">
            <strong class="score-text">{{ row.score }}</strong>
            <span class="score-max"> / {{ row.max_score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rank_in_class" label="班级排名" width="100">
          <template #default="{ row }">
            <span class="rank-badge">{{ row.rank_in_class ? `第 ${row.rank_in_class} 名` : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="教师评语/备注" min-width="180" show-overflow-tooltip />
      </el-table>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { listWeeklyScores, getWeeklyTrend } from '../../api/weeklyScores'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const subjects = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
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
  } finally {
    loading.value = false
  }
}

function render() {
  if (!chartRef.value || !trend.value.length) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: trend.value.map((d) => d.exam_date) },
    yAxis: { type: 'value', name: '分数' },
    series: [
      {
        type: 'line',
        smooth: true,
        data: trend.value.map((d) => d.score),
        itemStyle: { color: '#2f5bff' },
        areaStyle: { color: 'rgba(37,99,235,0.08)' },
      },
    ],
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
  })
}

watch(subject, load)
onMounted(load)
</script>

<style scoped>
.student-weekly-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.header-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
}

.filter-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.chart-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  padding: 16px 20px;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-head .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2f5bff;
}

.card-head .title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.chart-container {
  height: 260px;
  width: 100%;
}

.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
  padding: 16px 18px;
}

.subject-badge {
  font-size: 11.5px;
  font-weight: 600;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 7px;
  border-radius: 6px;
}

.score-text {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}

.score-max {
  font-size: 12px;
  color: #94a3b8;
}

.rank-badge {
  font-size: 12px;
  color: #475569;
}
</style>
