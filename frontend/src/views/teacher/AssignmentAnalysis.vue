<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">单次作业分析</span>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div v-loading="loading">
      <template v-if="data">
        <el-row :gutter="16" style="margin-bottom: 16px">
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat"><div class="num">{{ data.submission_count }}</div><div class="label">已确认提交</div></div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat"><div class="num">{{ data.average_score }}%</div><div class="label">平均得分率</div></div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat"><div class="num">{{ (data.pass_rate * 100).toFixed(0) }}%</div><div class="label">及格率</div></div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat"><div class="num">{{ data.question_accuracy.length }}</div><div class="label">题目数</div></div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-bottom: 16px">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>成绩分布</template>
              <EChart v-if="distOption" :option="distOption" />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>各题正确率</template>
              <EChart v-if="qOption" :option="qOption" />
              <el-empty v-else description="暂无题目数据" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>本作业薄弱知识点</template>
              <el-empty v-if="!data.weak_knowledge_points.length" description="暂无薄弱点" :image-size="60" />
              <el-table v-else :data="data.weak_knowledge_points" size="small">
                <el-table-column prop="name" label="知识点" show-overflow-tooltip />
                <el-table-column label="正确率" width="140">
                  <template #default="{ row }">
                    <el-progress :percentage="Math.round(row.mastery_score * 100)" :stroke-width="10"
                      :status="row.mastery_score < 0.6 ? 'exception' : row.mastery_score < 0.85 ? 'warning' : 'success'" />
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>主要错误类型</template>
              <el-empty v-if="!data.common_errors.length" description="暂无错误类型记录" :image-size="60" />
              <el-table v-else :data="data.common_errors" size="small">
                <el-table-column prop="error_type" label="错误类型" show-overflow-tooltip />
                <el-table-column prop="count" label="次数" width="80" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </template>
      <el-empty v-else-if="!loading" description="暂无分析数据" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getAssignmentAnalysis } from '../../api/analytics'
import EChart from '../../components/EChart.vue'

const route = useRoute()
const data = ref(null)
const loading = ref(false)

const DIST_LABELS = [
  { key: 'ge90', label: '90分以上' },
  { key: 'ge80', label: '80~89' },
  { key: 'ge70', label: '70~79' },
  { key: 'ge60', label: '60~69' },
  { key: 'lt60', label: '60分以下' },
]

const distOption = computed(() => {
  if (!data.value) return null
  const labels = DIST_LABELS.filter((d) => data.value.score_distribution[d.key] > 0)
  if (!labels.length) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: labels.map((d) => d.label) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'bar', barWidth: 40, data: labels.map((d) => data.value.score_distribution[d.key]) }],
  }
})

const qOption = computed(() => {
  if (!data.value?.question_accuracy.length) return null
  const rows = [...data.value.question_accuracy].sort((a, b) => a.accuracy - b.accuracy)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const row = rows[params[0].dataIndex]
        return `${row.content}<br/>正确率：${(row.accuracy * 100).toFixed(0)}%`
      },
    },
    grid: { left: 180, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', min: 0, max: 1, name: '正确率' },
    yAxis: {
      type: 'category',
      data: rows.map((r, i) => `第${r.question_id}题`),
    },
    series: [
      {
        type: 'bar',
        data: rows.map((r) => ({
          value: r.accuracy,
          itemStyle: { color: r.accuracy < 0.6 ? '#f56c6c' : r.accuracy < 0.85 ? '#e6a23c' : '#67c23a' },
        })),
        label: { show: true, formatter: (p) => `${(p.value * 100).toFixed(0)}%`, position: 'right' },
      },
    ],
  }
})

async function load() {
  loading.value = true
  try {
    data.value = await getAssignmentAnalysis(route.params.id)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stat {
  text-align: center;
  padding: 8px 0;
}
.stat .num {
  font-size: 26px;
  font-weight: 600;
  color: #303133;
}
.stat .label {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}
</style>
