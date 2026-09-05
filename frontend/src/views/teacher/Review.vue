<template>
  <div class="page review-manage-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">AI 作业批改与教师复核</h1>
        <p class="header-desc">查阅 AI 初批结果，对主观题作答与得分明细进行复核确认。</p>
      </div>
    </div>

    <div class="review-surface">
      <div class="filter-bar">
        <div class="tabs-wrap">
          <el-radio-group v-model="active" @change="load">
            <el-radio-button value="pending">待复核 (需要处理)</el-radio-button>
            <el-radio-button value="confirmed">已确认完成</el-radio-button>
          </el-radio-group>
        </div>
        <div class="select-wrap">
          <el-select v-model="filters.assignment_id" placeholder="按作业筛选" clearable style="width: 220px" @change="load">
            <el-option v-for="a in assignments" :key="a.id" :label="a.title" :value="a.id" />
          </el-select>
        </div>
      </div>

      <el-table :data="rows" v-loading="loading" empty-text="当前分类下暂无提交记录" style="width: 100%">
        <el-table-column prop="student_name" label="学生姓名" width="130">
          <template #default="{ row }">
            <strong>{{ row.student_name || '学生' }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="assignment_title" label="所属作业" min-width="180" show-overflow-tooltip />
        <el-table-column label="得分情况" width="130">
          <template #default="{ row }">
            <span class="score-text">{{ row.total_score ?? '—' }}</span>
            <span class="score-max"> / {{ row.max_total }}</span>
          </template>
        </el-table-column>
        <el-table-column label="复核进度" width="170">
          <template #default="{ row }">
            <el-progress
              :percentage="progressPct(row)"
              :format="() => `${row.confirmed_count}/${row.answer_count} 题`"
              :stroke-width="7"
            />
          </template>
        </el-table-column>
        <el-table-column label="批改状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'teacher_reviewed' ? 'success' : 'warning'" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="提交时间" width="160" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openReview(row)">进入复核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listReviews } from '../../api/submissions'
import { listAssignments } from '../../api/assignments'

const router = useRouter()
const active = ref('pending')
const filters = ref({ assignment_id: null })
const rows = ref([])
const assignments = ref([])
const loading = ref(false)

const statusLabel = (s) => ({
  ai_graded: 'AI已批改',
  teacher_reviewed: '已复核',
  completed: '已完成',
  failed: '批改失败',
}[s] || s)

const progressPct = (r) => (r.answer_count ? Math.round((r.confirmed_count / r.answer_count) * 100) : 0)

function openReview(row) {
  router.push(`/teacher/reviews/${row.id}`)
}

async function load() {
  loading.value = true
  try {
    const params = { status: active.value, ...filters.value }
    if (!params.assignment_id) delete params.assignment_id
    rows.value = await listReviews(params)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    assignments.value = await listAssignments()
  } catch {
    assignments.value = []
  }
  await load()
})
</script>

<style scoped>
.review-manage-page {
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

.review-surface {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
  padding: 16px 18px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.score-text {
  font-weight: 700;
  color: var(--ink);
  font-size: 14px;
}

.score-max {
  color: #94a3b8;
  font-size: 12px;
}
</style>