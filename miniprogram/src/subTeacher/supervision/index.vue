<template>
  <view class="page">
    <WorkspaceLink />
    <text class="title">{{ auth.user?.supervisor_stage }}主管工作台</text>
    <text class="note">查看本学段所有老师的月度评定填写状态与学生月考成绩。</text>
    <view v-if="error"><text>{{ error }}</text><button size="mini" @click="load">重新加载</button></view>
    <text v-else-if="loading">加载中…</text>
    <template v-else-if="allowed">
      <view class="tabs"><button size="mini" :class="{ active: tab === 'writing' }" @click="tab = 'writing'">评定填写状态</button><button size="mini" :class="{ active: tab === 'exams' }" @click="tab = 'exams'">月考成绩</button></view>
      <MonthlyWritingStatus v-if="tab === 'writing'" :classes="classes" scope="supervision" />
      <MonthlyExamOverview v-else :classes="classes" scope="supervision" />
    </template>
  </view>
</template>
<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listSupervisionClasses } from '../../api/studentCases'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import MonthlyWritingStatus from '../../components/MonthlyWritingStatus.vue'
import MonthlyExamOverview from '../../components/MonthlyExamOverview.vue'
const auth = useAuthStore()
const classes = ref([]), loading = ref(true), error = ref(''), allowed = ref(false), tab = ref('writing')
async function load() {
  loading.value = true; error.value = ''; allowed.value = false
  try { await auth.refreshMe(); classes.value = await listSupervisionClasses(); allowed.value = true }
  catch (e) { error.value = e.message || '主管数据加载失败，请重试' }
  finally { loading.value = false }
}
onShow(load)
</script>
<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 24rpx; }.title { font-size: 34rpx; font-weight: 600; }.note { font-size: 26rpx; line-height: 1.6; color: var(--mp-body); }.tabs { display: flex; gap: 16rpx; }.tabs button { margin: 0; color: var(--mp-body); background: #fff; border: 1rpx solid var(--mp-line); border-radius: 8rpx; }.tabs .active { background: var(--mp-primary); border-color: var(--mp-primary); color: #fff; }
</style>
