<template>
  <view class="page monthly-page">
    <WorkspaceLink />
    <view class="monthly-heading">
      <text class="monthly-title">{{ subject }}月度评定</text>
      <text class="monthly-meta">{{ formatMonth(month) }}<template v-if="reports.length"> · {{ reports[0].student_name }}</template></text>
    </view>
    <LoadState :loading="loading" :error="error" @retry="load" />
    <template v-if="!loading && !error">
      <EmptyState v-if="!selected" title="暂无该科目评定" desc="评定可能已调整，请返回科目列表重新选择" />
      <view v-for="entry in selected ? selected.entries : []" :key="entry.key" class="monthly-content">
        <text class="monthly-author">{{ entry.teacher }}<template v-if="selected.entries.length > 1 && entry.className"> · {{ entry.className }}</template></text>
        <view v-for="section in reviewSections(entry.content)" :key="section.key" class="review-section">
          <text class="review-label">{{ section.label }}</text>
          <text class="review-content" selectable>{{ section.content }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import LoadState from '../../components/LoadState.vue'
import EmptyState from '../../components/EmptyState.vue'
import { formatMonth, monthlySubjects, reviewSections } from '../../utils/parentMonthlyReports'
import { useMonthlyReports } from './useMonthlyReports'

const { loading, error, reports, month, subject, load } = useMonthlyReports()
const selected = computed(() => monthlySubjects(reports.value).find(item => item.subject === subject.value))
</script>

<style scoped src="./monthly.css"></style>
