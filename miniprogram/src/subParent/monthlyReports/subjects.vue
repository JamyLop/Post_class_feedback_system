<template>
  <view class="page monthly-page">
    <WorkspaceLink />
    <view class="monthly-heading">
      <text class="monthly-title">{{ formatMonth(month) }}月度评定</text>
      <text v-if="reports.length" class="monthly-meta">{{ reports[0].student_name }} · 选择科目查看评定</text>
    </view>
    <LoadState :loading="loading" :error="error" @retry="load" />
    <template v-if="!loading && !error">
      <EmptyState v-if="!subjects.length" title="本月暂无可查阅的科目评定" desc="老师发布后即可在此查阅" />
      <view v-else class="monthly-list">
        <button v-for="item in subjects" :key="item.subject" class="monthly-row" hover-class="tap-active" @click="openSubject(item.subject)">
          <view class="monthly-row-body">
            <text class="monthly-row-title">{{ item.subject }}</text>
            <text class="monthly-meta">{{ teachers(item) }}</text>
          </view>
          <text class="monthly-arrow" aria-hidden="true">›</text>
        </button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import LoadState from '../../components/LoadState.vue'
import EmptyState from '../../components/EmptyState.vue'
import { formatMonth, monthlySubjects } from '../../utils/parentMonthlyReports'
import { useMonthlyReports } from './useMonthlyReports'

const { loading, error, reports, studentId, month, load } = useMonthlyReports()
const subjects = computed(() => monthlySubjects(reports.value))
function teachers(item) { return [...new Set(item.entries.map(entry => entry.teacher))].join('、') }
function openSubject(subject) {
  uni.navigateTo({ url: `/subParent/monthlyReports/detail?studentId=${studentId.value}&month=${month.value}&subject=${encodeURIComponent(subject)}` })
}
</script>

<style scoped src="./monthly.css"></style>
