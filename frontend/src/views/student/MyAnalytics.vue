<template>
  <div class="page student-analytics-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的学情与知识掌握</h1>
        <p class="header-desc">跟踪个人课后作业得分走势、知识点熟练度雷达与核心攻坚薄弱点。</p>
      </div>
    </div>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="15">
        <el-card shadow="never" class="analytics-card">
          <template #header>
            <div class="card-head-title">
              <span class="dot"></span>
              <span>作业成绩走势</span>
            </div>
          </template>
          <EChart v-if="trendOption" :option="trendOption" />
          <el-empty v-else description="暂无已确认的作业成绩" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="9">
        <el-card shadow="never" class="analytics-card">
          <template #header>
            <div class="card-head-title">
              <span class="dot is-warning"></span>
              <span>待攻坚薄弱点 TOP 5</span>
            </div>
          </template>
          <el-empty v-if="!weakPoints.length" description="暂无薄弱点" :image-size="60" />
          <el-table v-else :data="weakPoints" size="small">
            <el-table-column prop="name" label="知识点" show-overflow-tooltip />
            <el-table-column label="掌握度" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="Math.round(row.mastery_score * 100)"
                  :stroke-width="8"
                  :status="row.mastery_score < 0.6 ? 'exception' : row.mastery_score < 0.85 ? 'warning' : 'success'"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="analytics-card">
      <template #header>
        <div class="card-head-title">
          <span class="dot"></span>
          <span>学科知识点掌握度矩阵</span>
        </div>
      </template>
      <EChart v-if="masteryOption" :option="masteryOption" />
      <el-empty v-else description="暂无知识点掌握度数据，待教师确认批改后自动生成" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import {
  getStudentKnowledgeStats,
  getStudentLearningTrend,
  getStudentWeakPoints,
} from '../../api/analytics'
import EChart from '../../components/EChart.vue'

const auth = useAuthStore()
const stats = ref([])
const weakPoints = ref([])
const trend = ref({ points: [] })

const trendOption = computed(() => {
  const points = trend.value.points
  if (!points.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: points.map((p) => `作业#${p.assignment_id}`) },
    yAxis: { type: 'value', min: 0, max: 100, name: '得分率(%)' },
    series: [
      {
        type: 'line', smooth: true, data: points.map((p) => p.percent),
        markLine: { data: [{ yAxis: 60 }], label: { formatter: '及格线' } },
      },
    ],
  }
})

const masteryOption = computed(() => {
  if (!stats.value.length) return null
  const data = [...stats.value].sort((a, b) => a.mastery_score - b.mastery_score)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const row = data[params[0].dataIndex]
        return `${row.name}<br/>掌握度：${(row.mastery_score * 100).toFixed(0)}%<br/>对/错：${row.correct_count}/${row.wrong_count}`
      },
    },
    grid: { left: 120, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', min: 0, max: 1, name: '掌握度' },
    yAxis: { type: 'category', data: data.map((r) => r.name) },
    series: [
      {
        type: 'bar',
        data: data.map((r) => ({
          value: r.mastery_score,
          itemStyle: { color: r.mastery_score < 0.6 ? '#f56c6c' : r.mastery_score < 0.85 ? '#e6a23c' : '#67c23a' },
        })),
        label: { show: true, formatter: (p) => `${(p.value * 100).toFixed(0)}%`, position: 'right' },
      },
    ],
  }
})

onMounted(async () => {
  const sid = auth.user?.id
  if (!sid) return
  const [s, w, t] = await Promise.all([
    getStudentKnowledgeStats(sid),
    getStudentWeakPoints(sid, { top_n: 5 }),
    getStudentLearningTrend(sid),
  ])
  stats.value = s
  weakPoints.value = w
  trend.value = t
})
</script>

<style scoped>
.student-analytics-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.analytics-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
}

.card-head-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2f5bff;
}

.dot.is-warning {
  background: #d97706;
}
</style>
