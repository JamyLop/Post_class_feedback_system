<template>
  <div class="page assignments-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">作业发布与监控</h1>
        <p class="header-desc">发布课后作业、跟踪各班提交进度并查阅作答学情诊断。</p>
      </div>
      <el-button type="primary" @click="$router.push('/teacher/assignments/new')">
        <el-icon><Plus /></el-icon>新建作业
      </el-button>
    </div>

    <div class="table-card">
      <el-table :data="assignments" v-loading="loading" empty-text="暂无作业记录" style="width: 100%">
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column prop="title" label="作业标题" min-width="200">
          <template #default="{ row }">
            <strong class="assignment-title-text">{{ row.title }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="学科" width="100">
          <template #default="{ row }">
            <span class="subject-badge">{{ row.subject || '综合' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="班级" width="120">
          <template #default="{ row }">
            <span>班级#{{ row.class_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="题目数" width="100">
          <template #default="{ row }">
            <span class="q-count-badge">{{ row.questions?.length || 0 }} 题</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusMap[row.status] || 'info'" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}`)">作业详情</el-button>
            <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}/submissions`)">批改提交</el-button>
            <el-button link type="primary" @click="$router.push(`/teacher/assignments/${row.id}/analysis`)">统计分析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { listAssignments } from '../../api/assignments'

const assignments = ref([])
const loading = ref(false)
const statusMap = { draft: 'info', published: 'success', closed: 'warning', archived: 'info' }

function statusLabel(s) {
  return { draft: '草稿', published: '已发布', closed: '已截止', archived: '已归档' }[s] || s
}

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
.assignments-page {
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

.q-count-badge {
  font-size: 12px;
  color: #475569;
  font-family: monospace;
}
</style>
