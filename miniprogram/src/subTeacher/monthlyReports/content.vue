<template>
  <view class="page reader-page">
    <WorkspaceLink />
    <view class="reader-heading">
      <text class="reader-title">{{ subject }}月度评定</text>
      <template v-if="report">
        <text class="reader-meta">{{ report.student_name || `学生#${report.student_id}` }} · {{ formatMonth(report.month_label) }}</text>
        <text class="reader-meta">{{ report.class_name }} · {{ status }}</text>
      </template>
    </view>
    <LoadState :loading="loading" :error="error" @retry="load" />
    <template v-if="!loading && !error && report">
      <EmptyState v-if="!selected" title="暂无该科目评定" desc="评定可能已调整，请返回科目列表重新选择" />
      <view v-for="entry in selected ? selected.entries : []" :key="entry.key" class="reader-content">
        <text class="reader-author">{{ entry.teacher }}</text>
        <template v-if="entry.content?.trim()">
          <view v-for="section in reviewSections(entry.content)" :key="section.key" class="reader-section">
            <text class="reader-label">{{ section.label }}</text>
            <text class="reader-text" selectable>{{ section.content }}</text>
          </view>
        </template>
        <EmptyState v-else title="该科目尚未填写" desc="对应老师填写后即可在此查阅" />
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import LoadState from '../../components/LoadState.vue'
import EmptyState from '../../components/EmptyState.vue'
import { formatMonth, reviewSections } from '../../utils/parentMonthlyReports'
import { useAdminMonthlyReport } from './useAdminMonthlyReport'

const { report, loading, error, subject, subjects, status, load } = useAdminMonthlyReport()
const selected = computed(() => subjects.value.find(item => item.subject === subject.value))
</script>

<style scoped src="./reader.css"></style>
