<template>
  <view class="page">
    <view v-if="loading" class="tip">加载中…</view>
    <template v-else-if="task">
      <view class="header">
        <view class="head-row">
          <text class="subject-tag">{{ task.subject || '综合' }}</text>
          <text class="cadence">{{ cadenceLabel(task.cadence) }}</text>
          <text class="status">{{ statusLabel(task.status) }}</text>
        </view>
        <text class="h1">{{ task.title }}</text>
        <text class="desc">{{ task.description || '暂无描述' }}</text>
        <view class="meta">
          <text>{{ task.starts_on }} 至 {{ task.due_on }}</text>
          <text v-if="caseId" class="link" @click="goCase">查看所属档案 →</text>
        </view>
      </view>

      <view class="section">
        <text class="section-title">执行记录 · {{ checkins.length }} 条</text>
        <view v-if="checkins.length">
          <Timeline :items="timelineItems" />
        </view>
        <EmptyState v-else title="暂无执行记录" desc="班主任尚未录入打卡" />
      </view>
    </template>
    <EmptyState v-else title="任务不存在" desc="参数错误或无权查看" />
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStudentCase } from '../../api/studentCases'
import Timeline from '../../components/Timeline.vue'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const task = ref(null)
const checkins = ref([])
const caseId = ref('')

function cadenceLabel(v) { return { daily:'日计划', weekly:'周计划', monthly:'月计划'}[v] || v || '-' }
function statusLabel(v) { return { pending:'待执行', in_progress:'执行中', completed:'已完成', cancelled:'已取消'}[v] || v }
function goCase() {
  if (!caseId.value) return
  uni.navigateTo({ url: `/subParent/caseDetail/index?id=${caseId.value}` })
}

const timelineItems = computed(() => checkins.value.map(c => ({
  title: `${c.completion_rate}% · ${c.checked_in_at?.slice(0,16).replace('T',' ') || ''}`,
  desc: c.self_check || '—',
  time: c.checked_in_at?.slice(0,16).replace('T',' '),
})))

async function load() {
  loading.value = true
  try {
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1]
    const opts = cur.options || cur.$page?.options || {}
    const tId = Number(opts.taskId || opts.task_id || opts.id)
    const cId = opts.caseId || opts.case_id || ''
    caseId.value = cId
    if (!tId) throw new Error('缺少 taskId')
    // 若带 caseId 直接用详情聚合，避免额外接口
    let detail = null
    if (cId) {
      detail = await getStudentCase(cId)
    } else {
      // 无 caseId 时尝试通过任务列表反查（降级：需先拉可见档案列表再找）
      // 为简化，提示需要 caseId
      throw new Error('请从档案任务列表进入')
    }
    const found = (detail.tasks || []).find(t => t.id === tId)
    if (!found) throw new Error('任务不存在或已移除')
    task.value = found
    checkins.value = (detail.task_checkins || []).filter(c => c.task_id === tId).sort((a,b)=> new Date(b.checked_in_at)-new Date(a.checked_in_at))
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding:24rpx 20rpx 48rpx; display:flex; flex-direction:column; gap:20rpx; }
.tip { text-align:center; color:#64748b; padding:48rpx; }
.header { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:28rpx; }
.head-row { display:flex; gap:12rpx; align-items:center; flex-wrap:wrap; margin-bottom:12rpx; }
.subject-tag { font-size:20rpx; color:#2563eb; background:#eff6ff; border:1rpx solid #bfdbfe; padding:4rpx 10rpx; border-radius:999rpx; }
.cadence { font-size:20rpx; color:#64748b; background:#f1f5f9; padding:4rpx 10rpx; border-radius:999rpx; }
.status { font-size:20rpx; color:#0f172a; background:#f8fafc; border:1rpx solid #e2e8f0; padding:4rpx 10rpx; border-radius:999rpx; }
.h1 { font-size:30rpx; font-weight:700; color:#0f172a; display:block; }
.desc { font-size:24rpx; color:#475569; display:block; margin-top:8rpx; line-height:1.6; white-space:pre-wrap; }
.meta { display:flex; justify-content:space-between; align-items:center; margin-top:12rpx; font-size:22rpx; color:#94a3b8; }
.link { color:#2563eb; }
.section { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:24rpx; }
.section-title { font-size:26rpx; font-weight:600; color:#0f172a; display:block; margin-bottom:16rpx; }
</style>
