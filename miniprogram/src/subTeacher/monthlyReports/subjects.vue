<template>
  <view class="page reader-page">
    <WorkspaceLink />
    <view class="reader-heading">
      <text class="reader-title">月度评定 · 选择科目</text>
      <template v-if="report">
        <text class="reader-meta">{{ report.student_name || `学生#${report.student_id}` }} · {{ formatMonth(report.month_label) }}</text>
        <text class="reader-meta">{{ report.class_name }} · {{ status }}</text>
      </template>
    </view>
    <LoadState :loading="loading" :error="error" @retry="load" />
    <template v-if="!loading && !error && report">
      <text class="reader-meta">应评科目依据学生入学评定及任课老师关联生成；缺少科目时请检查相关信息。</text>
      <text v-if="statusLoading" class="reader-meta">正在加载科目填写状态…</text>
      <view v-else-if="statusError" class="reader-meta">{{ statusError }} <text @click="loadWritingStatus">点击重试</text></view>
      <view class="reader-list">
        <button v-for="item in displaySubjects" :key="item.subject" class="reader-row" hover-class="tap-active" @click="openSubject(item)">
          <view class="reader-row-body">
            <view class="reader-row-head"><text class="reader-subject">{{ item.subject }}</text><text class="reader-meta">{{ item.written ? '已填写' : '未填写' }}</text></view>
            <text class="reader-meta">{{ item.teacher }}{{ item.assignmentRequired ? ' · 待确认任课老师' : '' }}</text>
          </view>
          <text v-if="item.written && item.reportId" class="reader-arrow" aria-hidden="true">›</text>
        </button>
      </view>
      <text v-if="report.error_message" class="reader-meta">{{ report.error_message }}</text>
      <button v-if="report.can_publish && report.status === 'generated' && !readOnly" class="reader-publish" :disabled="publishing" :loading="publishing" @click="publish">发布本月评定</button>
    </template>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import LoadState from '../../components/LoadState.vue'
import { listMonthlyWritingStatus, publishMonthlyReport } from '../../api/monthlyReports'
import { adminMonthlySubjects, formatMonth } from '../../utils/parentMonthlyReports'
import { useAdminMonthlyReport } from './useAdminMonthlyReport'

const { report, loading, error, reportId, readOnly, status, load } = useAdminMonthlyReport()
const publishing = ref(false)
const statusItems = ref([])
const statusLoading = ref(false)
const statusError = ref('')
const displaySubjects = computed(() => adminMonthlySubjects(report.value, statusItems.value))
let statusRequest = 0
async function loadWritingStatus() {
  const current = report.value
  const request = ++statusRequest
  statusItems.value = []
  statusError.value = ''
  if (!current) { statusLoading.value = false; return }
  statusLoading.value = true
  try {
    const items = []
    let total = 0
    do {
      const data = await listMonthlyWritingStatus({ month_label: current.month_label, class_id: current.class_id, student_id: current.student_id, view: 'items', limit: 200, offset: items.length })
      if (!Array.isArray(data.items) || typeof data.filtered_total !== 'number') throw new Error('invalid status')
      total = data.filtered_total
      if (!data.items.length && items.length < total) throw new Error('incomplete status')
      items.push(...data.items)
    } while (items.length < total)
    if (request !== statusRequest) return
    statusItems.value = items
    if (!items.length) statusError.value = '未能获取该学生的完整科目状态，以下仅显示已有评定。'
  } catch (_) {
    if (request === statusRequest) statusError.value = '科目状态加载失败，以下仅显示已有评定。'
  } finally { if (request === statusRequest) statusLoading.value = false }
}
watch(report, loadWritingStatus, { immediate: true })
function openSubject(item) {
  if (!item.written || !item.reportId) return
  uni.navigateTo({ url: `/subTeacher/monthlyReports/content?id=${item.reportId}&subject=${encodeURIComponent(item.subject)}${readOnly.value ? '&readonly=1' : ''}` })
}
function publish() {
  if (publishing.value) return
  uni.showModal({
    title: '确认发布',
    content: '将发布该学生本月整份评定，发布后家长可查阅，确认发布？',
    success: async result => {
      if (!result.confirm || publishing.value) return
      publishing.value = true
      try {
        report.value = await publishMonthlyReport(reportId.value)
        uni.showToast({ title: '发布成功', icon: 'success' })
      } catch (_) { /* 请求层显示服务端错误，保留页面内容供重试。 */ }
      finally { publishing.value = false }
    },
  })
}
</script>

<style scoped src="./reader.css"></style>
