<template>
  <section class="page supervision-page">
    <header><h1>{{ auth.user?.supervisor_stage }}主管工作台</h1><p>查看本学段所有老师的月度评定填写状态与学生月考成绩。</p></header>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button @click="load">重新加载</el-button></el-alert>
    <el-skeleton v-else-if="loading" :rows="5" animated />
    <template v-else-if="allowed">
      <el-tabs v-model="tab"><el-tab-pane label="月度评定填写状态" name="writing" /><el-tab-pane label="月考成绩" name="exams" /></el-tabs>
      <MonthlyWritingStatus v-if="tab === 'writing'" :classes="classes" scope="supervision" />
      <MonthlyExamOverview v-else :classes="classes" scope="supervision" />
    </template>
  </section>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { listSupervisionClasses } from '../../api/users'
import MonthlyWritingStatus from '../../components/MonthlyWritingStatus.vue'
import MonthlyExamOverview from '../../components/MonthlyExamOverview.vue'
const auth = useAuthStore()
const classes = ref([]), loading = ref(true), error = ref(''), allowed = ref(false), tab = ref('writing')
async function load() {
  loading.value = true; error.value = ''; allowed.value = false
  try {
    await auth.refreshMe()
    classes.value = await listSupervisionClasses(); allowed.value = true
  } catch (e) { error.value = e.response?.data?.detail || '主管数据加载失败，请重试' }
  finally { loading.value = false }
}
onMounted(load)
</script>
<style scoped>
.supervision-page { display: flex; flex-direction: column; gap: 20px; }h1 { margin: 0 0 8px; font-size: var(--font-size-page-title); }p { margin: 0; color: var(--ink-secondary); line-height: 1.6; }
</style>
