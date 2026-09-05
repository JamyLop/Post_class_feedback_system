<template>
  <div class="page student-assignments-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">课后作业任务</h1>
        <p class="header-desc">及时完成任课教师发布的课后练习，查阅题目解析与批改报告。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新作业</el-button>
    </div>

    <div class="table-card">
      <el-table :data="assignments" v-loading="loading" empty-text="暂无待完成的作业任务" style="width: 100%">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column prop="title" label="作业名称" min-width="220">
          <template #default="{ row }">
            <strong class="assignment-title-text">{{ row.title }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="学科" width="110">
          <template #default="{ row }">
            <span class="subject-badge">{{ row.subject || '综合' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="题目总数" width="110">
          <template #default="{ row }">
            <span class="q-count">{{ row.questions?.length || 0 }} 题</span>
          </template>
        </el-table-column>
        <el-table-column prop="due_at" label="截止提交时间" min-width="170">
          <template #default="{ row }">
            <span class="due-text">{{ row.due_at || '未设置截止时间' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="$router.push(`/student/assignments/${row.id}`)">
              开始作答
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listAssignments } from '../../api/assignments'

const assignments = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    assignments.value = await listAssignments()
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.student-assignments-page {
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

.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  overflow: hidden;
  padding: 16px 18px;
}

.assignment-title-text {
  color: var(--ink);
  font-weight: 600;
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

.q-count {
  font-size: 12.5px;
  color: #475569;
}

.due-text {
  font-size: 12.5px;
  color: #64748b;
  font-family: monospace;
}
</style>
