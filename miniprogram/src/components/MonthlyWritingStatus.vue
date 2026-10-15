<template>
  <view class="writing-query">
    <view class="query-filters">
      <view class="field"><text>班级</text><picker :range="classNames" :value="classIndex" @change="changeClass"><view class="picker">{{ classNames[classIndex] }} ▾</view></picker></view>
      <view class="field"><text>月份</text><picker mode="date" fields="month" :value="month" @change="changeMonth"><view class="picker">{{ month }} ▾</view></picker></view>
      <view class="field"><text>填写状态</text><picker :range="statusNames" :value="statusIndex" @change="changeStatus"><view class="picker">{{ statusNames[statusIndex] }} ▾</view></picker></view>
    </view>
    <view class="search"><input v-model="keyword" placeholder="搜索学生" confirm-type="search" @confirm="query" /><button size="mini" :disabled="loading" @click="query">查询</button></view>
    <text class="note">按本人负责的评定项统计，德育与学科分别显示。</text>
    <view v-if="error" class="message"><text>填写状态加载失败</text><button size="mini" @click="load">重试</button></view>
    <template v-else>
      <text class="counts">共 {{ result.total }} 项 · 已填写 {{ result.written }} 项 · 未填写 {{ result.unwritten }} 项</text>
      <text v-if="loading" class="message">加载中…</text>
      <text v-else-if="!result.items.length" class="message">当前条件下没有学生，请调整筛选条件</text>
      <view v-else class="results">
        <view v-for="row in result.items" :key="`${row.class_id}-${row.student_id}-${row.teacher_role}`" class="result-row">
          <view class="row-title"><text class="name">{{ row.student_name }}</text><text class="tag" :class="{ written: row.writing_status === 'written' }">{{ row.writing_status === 'written' ? '已填写' : '未填写' }}</text></view>
          <text class="meta">{{ row.class_name }} · {{ row.month_label }} · {{ row.subject }}</text>
          <button size="mini" class="write-button" @click="openRow(row)">{{ row.writing_status === 'written' ? '查看 / 修改' : '去填写' }}</button>
        </view>
      </view>
      <view v-if="result.filtered_total > 50" class="pagination"><button size="mini" :disabled="page === 1 || loading" @click="turnPage(-1)">上一页</button><text>{{ page }} / {{ Math.ceil(result.filtered_total / 50) }}</text><button size="mini" :disabled="page * 50 >= result.filtered_total || loading" @click="turnPage(1)">下一页</button></view>
    </template>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { listMonthlyWritingStatus } from '../api/monthlyReports'
const props = defineProps({ classes: { type: Array, default: () => [] } })
const classIndex = ref(0)
const classNames = computed(() => ['全部班级', ...props.classes.map(c => c.name)])
const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const statusNames = ['全部', '已填写', '未填写']
const statusValues = ['', 'written', 'unwritten']
const statusIndex = ref(0)
const keyword = ref('')
const page = ref(1)
const loading = ref(false)
const error = ref(false)
const result = ref({ total: 0, written: 0, unwritten: 0, filtered_total: 0, items: [] })
let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true
  error.value = false
  try {
    const params = { month_label: month.value, keyword: keyword.value.trim(), limit: 50, offset: (page.value - 1) * 50 }
    const cid = props.classes[classIndex.value - 1]?.id
    if (cid) params.class_id = cid
    if (statusValues[statusIndex.value]) params.writing_status = statusValues[statusIndex.value]
    const data = await listMonthlyWritingStatus(params)
    if (id === requestId) result.value = data
  } catch { if (id === requestId) error.value = true }
  finally { if (id === requestId) loading.value = false }
}
function query() { page.value = 1; load() }
function changeClass(e) { classIndex.value = Number(e.detail.value); query() }
function changeMonth(e) { month.value = e.detail.value; query() }
function changeStatus(e) { statusIndex.value = Number(e.detail.value); query() }
function turnPage(delta) { page.value += delta; load() }
function openRow(row) {
  uni.navigateTo({ url: `/subTeacher/monthlyReports/generate?classId=${row.class_id}&studentId=${row.student_id}&month=${row.month_label}&evaluationRole=${row.teacher_role}` })
}
defineExpose({ load })
onMounted(load)
</script>

<style scoped>
.writing-query { background: #fff; border: 1rpx solid var(--mp-line); border-radius: 10rpx; padding: 24rpx; display: flex; flex-direction: column; gap: 20rpx; }
.query-filters { display: flex; flex-wrap: wrap; gap: 16rpx; }
.field { flex: 1; min-width: 180rpx; font-size: 24rpx; color: var(--mp-body, #445269); }
.picker { margin-top: 8rpx; padding: 16rpx 12rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; color: var(--mp-ink); }
.search { display: flex; align-items: center; gap: 16rpx; }
.search input { min-width: 0; flex: 1; padding: 16rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; font-size: 26rpx; }
.search button { flex: none; margin: 0; }
.note, .meta { display: block; color: var(--mp-body, #445269); font-size: 24rpx; line-height: 1.6; }
.counts { color: var(--mp-ink); font-size: 26rpx; }
.message { display: block; text-align: center; padding: 24rpx 0; font-size: 26rpx; color: var(--mp-body, #445269); }
.result-row { padding: 22rpx 0; border-top: 1rpx solid var(--mp-line); }
.row-title { display: flex; gap: 16rpx; align-items: center; margin-bottom: 8rpx; }
.name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.tag { font-size: 24rpx; color: #865c1e; background: #fbf1df; border-radius: 6rpx; padding: 4rpx 12rpx; }
.tag.written { color: #286349; background: #eaf3ee; }
.write-button { margin: 12rpx 0 0; color: var(--mp-primary); background: #fff; }
.pagination { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; font-size: 24rpx; }
.pagination button { margin: 0; }
</style>
