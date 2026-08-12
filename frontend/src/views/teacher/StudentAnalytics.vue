<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">学生学情</span>
      <el-button v-if="studentId" link type="primary" @click="onRecompute">重算掌握度</el-button>
    </div>

    <el-form inline>
      <el-form-item label="班级">
        <el-select v-model="classId" placeholder="选择班级" @change="onClassChange" style="width: 200px">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="学生">
        <el-select v-model="studentId" placeholder="选择学生" filterable @change="load" style="width: 200px">
          <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </el-form-item>
    </el-form>

    <template v-if="studentId">
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="16">
          <el-card shadow="never">
            <template #header>成绩趋势</template>
            <EChart v-if="trendOption" :option="trendOption" />
            <el-empty v-else description="暂无已确认的作业成绩" :image-size="60" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never">
            <template #header>薄弱知识点 TOP {{ weakPoints.length || 5 }}</template>
            <el-empty v-if="!weakPoints.length" description="暂无薄弱点" :image-size="60" />
            <el-table v-else :data="weakPoints" size="small">
              <el-table-column prop="name" label="知识点" show-overflow-tooltip />
              <el-table-column label="掌握度" width="130">
                <template #default="{ row }">
                  <el-progress :percentage="Math.round(row.mastery_score * 100)" :stroke-width="10"
                    :status="row.mastery_score < 0.6 ? 'exception' : row.mastery_score < 0.85 ? 'warning' : 'success'" />
                </template>
              </el-table-column>
              <el-table-column label="趋势" width="70">
                <template #default="{ row }">
                  <el-tag size="small" :type="trendTag(row.trend)">{{ trendLabel(row.trend) }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never">
        <template #header>知识点掌握度</template>
        <EChart v-if="masteryOption" :option="masteryOption" />
        <el-empty v-else description="暂无知识点掌握度数据，教师复核确认后自动生成" :image-size="60" />
      </el-card>

      <el-card shadow="never" style="margin-top: 16px">
        <template #header>重复错误</template>
        <el-empty v-if="!repeatedErrors.length" description="暂无重复错误" :image-size="60" />
        <el-table v-else :data="repeatedErrors" size="small">
          <el-table-column prop="error_type" label="错误类型" show-overflow-tooltip />
          <el-table-column prop="count" label="出现次数" width="100" />
        </el-table>
      </el-card>
    </template>
    <el-empty v-else description="请先选择班级和学生" :image-size="80" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listClasses, listStudents } from '../../api/classes'
import {
  getStudentKnowledgeStats,
  getStudentLearningTrend,
  getStudentRepeatedErrors,
  getStudentWeakPoints,
  recomputeStudentStats,
} from '../../api/analytics'
import EChart from '../../components/EChart.vue'

const classes = ref([])
const students = ref([])
const classId = ref(null)
const studentId = ref(null)
const stats = ref([])
const weakPoints = ref([])
const trend = ref({ points: [] })
const repeatedErrors = ref([])

const trendTag = (t) => ({ up: 'success', down: 'danger', stable: 'info', new: 'info' }[t] || 'info')
const trendLabel = (t) => ({ up: '上升', down: '下降', stable: '平稳', new: '新' }[t] || t)

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

async function load() {
  if (!studentId.value) return
  const scope = { class_id: classId.value }
  const [s, w, t, e] = await Promise.all([
    getStudentKnowledgeStats(studentId.value, scope),
    getStudentWeakPoints(studentId.value, { ...scope, top_n: 5 }),
    getStudentLearningTrend(studentId.value, scope),
    getStudentRepeatedErrors(studentId.value, { ...scope, top_n: 10, min_count: 2 }),
  ])
  stats.value = s
  weakPoints.value = w
  trend.value = t
  repeatedErrors.value = e
}

async function onClassChange() {
  studentId.value = null
  stats.value = []
  weakPoints.value = []
  trend.value = { points: [] }
  repeatedErrors.value = []
  students.value = classId.value ? await listStudents(classId.value) : []
}

async function onRecompute() {
  try {
    stats.value = await recomputeStudentStats(studentId.value, { class_id: classId.value })
    ElMessage.success('已重算掌握度')
  } catch (e) {
    ElMessage.error('重算失败')
  }
}

onMounted(async () => {
  classes.value = await listClasses()
})
</script>
