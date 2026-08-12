<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">班级学情</span>
    </div>

    <el-form inline>
      <el-form-item label="班级">
        <el-select v-model="classId" placeholder="选择班级" @change="load" style="width: 220px">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
    </el-form>

    <template v-if="data">
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="8">
          <el-card shadow="never">
            <template #header>班级概况</template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="已确认提交数">{{ data.submission_count }} 份</el-descriptions-item>
              <el-descriptions-item label="平均得分率">{{ data.average_score }}%</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card shadow="never">
            <template #header>成绩分布</template>
            <EChart v-if="distOption" :option="distOption" />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>知识点整体正确率</template>
            <EChart v-if="kpOption" :option="kpOption" />
            <el-empty v-else description="暂无知识点数据" :image-size="60" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>班级薄弱知识点排行</template>
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
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>共性错误</template>
            <el-empty v-if="!data.common_errors.length" description="暂无错误类型记录" :image-size="60" />
            <el-table v-else :data="data.common_errors" size="small">
              <el-table-column prop="error_type" label="错误类型" show-overflow-tooltip />
              <el-table-column prop="count" label="次数" width="80" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>最近一次作业未提交学生</template>
            <el-empty v-if="!data.unsubmitted_students.length" description="暂无未提交学生" :image-size="60" />
            <el-table v-else :data="data.unsubmitted_students" size="small">
              <el-table-column prop="student_id" label="ID" width="80" />
              <el-table-column prop="name" label="姓名" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>
    <el-empty v-else description="请先选择班级" :image-size="80" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { listClasses } from '../../api/classes'
import { getClassAnalytics } from '../../api/analytics'
import EChart from '../../components/EChart.vue'

const classes = ref([])
const classId = ref(null)
const data = ref(null)

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

const kpOption = computed(() => {
  if (!data.value?.knowledge_accuracy.length) return null
  const rows = [...data.value.knowledge_accuracy].sort((a, b) => a.mastery_score - b.mastery_score)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const row = rows[params[0].dataIndex]
        return `${row.name}<br/>正确率：${(row.mastery_score * 100).toFixed(0)}%<br/>对/错：${row.correct_count}/${row.wrong_count}`
      },
    },
    grid: { left: 120, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', min: 0, max: 1, name: '正确率' },
    yAxis: { type: 'category', data: rows.map((r) => r.name) },
    series: [
      {
        type: 'bar',
        data: rows.map((r) => ({
          value: r.mastery_score,
          itemStyle: { color: r.mastery_score < 0.6 ? '#f56c6c' : r.mastery_score < 0.85 ? '#e6a23c' : '#67c23a' },
        })),
        label: { show: true, formatter: (p) => `${(p.value * 100).toFixed(0)}%`, position: 'right' },
      },
    ],
  }
})

async function load() {
  if (!classId.value) return
  data.value = await getClassAnalytics(classId.value)
}

onMounted(async () => {
  classes.value = await listClasses()
})
</script>
