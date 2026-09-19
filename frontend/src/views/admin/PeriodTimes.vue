<template>
  <div class="page period-times-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">节次时间配置</h1>
        <p class="header-desc">配置每个节次对应的上课时间，排课时将自动显示。</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="table-card">
      <el-table :data="periodTimes" v-loading="loading" empty-text="暂无节次配置" style="width: 100%">
        <el-table-column prop="period" label="节次" width="120">
          <template #default="{ row }">
            <span class="period-badge">第 {{ row.period }} 节</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="200">
          <template #default="{ row }">
            <span v-if="editingPeriod !== row.period">{{ row.start_time }}</span>
            <el-time-picker
              v-else
              v-model="editForm.start_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="开始时间"
              style="width: 140px"
            />
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="200">
          <template #default="{ row }">
            <span v-if="editingPeriod !== row.period">{{ row.end_time }}</span>
            <el-time-picker
              v-else
              v-model="editForm.end_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="结束时间"
              style="width: 140px"
            />
          </template>
        </el-table-column>
        <el-table-column label="时长" width="120">
          <template #default="{ row }">
            {{ calcDuration(row.start_time, row.end_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="editingPeriod === row.period">
              <el-button link type="primary" @click="save(row.period)">保存</el-button>
              <el-button link @click="cancelEdit">取消</el-button>
            </template>
            <el-button v-else link type="primary" @click="startEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { listPeriodTimes, updatePeriodTime } from '../../api/period_times'

const periodTimes = ref([])
const loading = ref(false)
const editingPeriod = ref(null)
const editForm = reactive({ start_time: '', end_time: '' })

async function load() {
  loading.value = true
  try {
    periodTimes.value = await listPeriodTimes()
  } finally {
    loading.value = false
  }
}

function startEdit(row) {
  editingPeriod.value = row.period
  editForm.start_time = row.start_time
  editForm.end_time = row.end_time
}

function cancelEdit() {
  editingPeriod.value = null
}

async function save(period) {
  if (!editForm.start_time || !editForm.end_time) {
    ElMessage.warning('请填写开始和结束时间')
    return
  }
  if (editForm.start_time >= editForm.end_time) {
    ElMessage.warning('开始时间必须早于结束时间')
    return
  }
  try {
    await updatePeriodTime(period, { start_time: editForm.start_time, end_time: editForm.end_time })
    ElMessage.success('保存成功')
    editingPeriod.value = null
    await load()
  } catch {
    /* 拦截器已提示 */
  }
}

function calcDuration(start, end) {
  if (!start || !end) return '-'
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  const diff = (eh * 60 + em) - (sh * 60 + sm)
  if (diff <= 0) return '-'
  const mins = diff % 60
  const hours = Math.floor(diff / 60)
  return hours > 0 ? `${hours}小时${mins > 0 ? mins + '分钟' : ''}` : `${mins}分钟`
}

onMounted(load)
</script>

<style scoped>
.period-times-page {
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
  font-size: var(--font-size-page-title);
  font-weight: var(--font-weight-heading);
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
  overflow: hidden;
  padding: 16px 18px;
}

.period-badge {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 10px;
  border-radius: 6px;
}
</style>
