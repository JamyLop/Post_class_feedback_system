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
      <view class="reader-list">
        <button v-for="item in subjects" :key="item.subject" class="reader-row" hover-class="tap-active" @click="openSubject(item.subject)">
          <view class="reader-row-body">
            <view class="reader-row-head"><text class="reader-subject">{{ item.subject }}</text><text class="reader-meta">{{ item.entries.some(entry => entry.content?.trim()) ? '已填写' : '未填写' }}</text></view>
            <text class="reader-meta">{{ teachers(item) }}</text>
          </view>
          <text class="reader-arrow" aria-hidden="true">›</text>
        </button>
      </view>
      <text v-if="report.error_message" class="reader-meta">{{ report.error_message }}</text>
      <button v-if="report.can_publish && report.status === 'generated' && !readOnly" class="reader-publish" :disabled="publishing" :loading="publishing" @click="publish">发布本月评定</button>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import LoadState from '../../components/LoadState.vue'
import { publishMonthlyReport } from '../../api/monthlyReports'
import { formatMonth } from '../../utils/parentMonthlyReports'
import { useAdminMonthlyReport } from './useAdminMonthlyReport'

const { report, loading, error, reportId, readOnly, subjects, status, load } = useAdminMonthlyReport()
const publishing = ref(false)
function teachers(item) { return [...new Set(item.entries.map(entry => entry.teacher))].join('、') }
function openSubject(subject) {
  uni.navigateTo({ url: `/subTeacher/monthlyReports/content?id=${reportId.value}&subject=${encodeURIComponent(subject)}${readOnly.value ? '&readonly=1' : ''}` })
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
