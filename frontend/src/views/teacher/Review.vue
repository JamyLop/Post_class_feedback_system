<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">教师复核</span>
    </div>
    <el-form inline>
      <el-form-item label="作业">
        <el-select v-model="filters.assignment_id" placeholder="全部作业" clearable @change="load">
          <el-option v-for="a in assignments" :key="a.id" :label="a.title" :value="a.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <el-tabs v-model="active" @tab-change="load">
      <el-tab-pane label="待复核" name="pending" />
      <el-tab-pane label="已确认" name="confirmed" />
    </el-tabs>
    <el-table :data="rows" v-loading="loading" empty-text="暂无数据">
      <el-table-column prop="student_name" label="学生" width="120" />
      <el-table-column prop="assignment_title" label="作业" show-overflow-tooltip />
      <el-table-column label="总分" width="120">
        <template #default="{ row }">{{ row.total_score ?? '—' }} / {{ row.max_total }}</template>
      </el-table-column>
      <el-table-column label="复核进度" width="160">
        <template #default="{ row }">
          <el-progress :percentage="progressPct(row)" :format="() => `${row.confirmed_count}/${row.answer_count}`" />
        </template>
      </el-table-column>
      <el-table-column label="提交状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'teacher_reviewed' ? 'success' : 'warning'">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="submitted_at" label="提交时间" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openReview(row)">进入复核</el-button>
        </template>
      </el-table-column>
    </el-table>
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
  ai_graded: 'AI已批改', teacher_reviewed: '已复核', completed: '已完成', failed: '失败',
}[s] || s)
const progressPct = (r) => (r.answer_count ? Math.round((r.confirmed_count / r.answer_count) * 100) : 0)

function openReview(row) {
  router.push({ path: `/teacher/reviews/${row.submission_id}`, state: { row } })
}

async function load() {
  loading.value = true
  try {
    rows.value = await listReviews({ review_status: active.value, ...filters.value })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  assignments.value = await listAssignments()
  load()
})
</script>