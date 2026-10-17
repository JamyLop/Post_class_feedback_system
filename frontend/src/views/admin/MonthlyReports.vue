<template>
  <section class="page">
    <header class="page-head"><div><h1>月度评定</h1><p>查看全校、班级及学生各科填写情况，可单独调整各科评定的月份。</p></div></header>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button @click="loadClasses">重试</el-button></el-alert>
    <MonthlyWritingStatus v-else :classes="classes" />
  </section>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import MonthlyWritingStatus from '../../components/MonthlyWritingStatus.vue'
import { listClasses } from '../../api/classes'
const classes = ref([])
const error = ref('')
async function loadClasses() {
  try { classes.value = await listClasses(); error.value = '' }
  catch { error.value = '班级加载失败，请重试' }
}
onMounted(loadClasses)
</script>
