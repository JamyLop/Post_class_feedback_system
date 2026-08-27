<template>
  <section v-loading="loading" class="page">
    <div class="hero">
      <div><p>高三 · 我的成长主线</p><h1>我的一生一案</h1><span v-if="detail">第 {{ detail.version }} 版 · {{ labels[detail.status] }}</span></div>
      <div class="target"><small>我的升学目标</small><strong>{{ detail?.admission_target || '待老师确认' }}</strong></div>
    </div>
    <el-alert v-if="notFound" title="老师尚未发布你的正式方案" type="info" :closable="false" show-icon />
    <template v-if="detail">
      <div class="section-head"><div><h2>今日与近期任务</h2><p>完成后如实填写自查，不用追求“全完成”的表面数字。</p></div></div>
      <div v-if="detail.tasks.length" class="task-list">
        <article v-for="task in detail.tasks" :key="task.id" class="task">
          <div><el-tag size="small" effect="plain">{{ task.subject || '综合' }}</el-tag><h3>{{ task.title }}</h3><p>{{ task.description }}</p><small>{{ task.starts_on }} — {{ task.due_on }} · {{ task.status }}</small></div>
          <el-button type="primary" plain @click="openCheckin(task)">提交自查</el-button>
        </article>
      </div>
      <el-empty v-else description="当前没有待执行任务" />
      <div class="columns">
        <el-card shadow="never"><template #header><b>本阶段目标</b></template><div v-for="goal in detail.goals" :key="goal.id" class="goal"><span>{{ goal.title }}</span><b>{{ goal.target_value ?? '定性目标' }}</b></div><el-empty v-if="!detail.goals.length" description="暂无目标" :image-size="60" /></el-card>
        <el-card shadow="never"><template #header><b>教师反馈</b></template><div v-for="review in detail.reviews.slice(0, 5)" :key="review.id" class="review"><span>{{ review.problem || '执行情况正常' }}</span><small>{{ review.corrective_action }}</small></div><el-empty v-if="!detail.reviews.length" description="暂无反馈" :image-size="60" /></el-card>
      </div>
    </template>

    <el-dialog v-model="dialog" title="任务完成自查" width="480px">
      <el-form label-position="top"><el-form-item label="完成度"><el-slider v-model="form.completion_rate" show-input /></el-form-item><el-form-item label="自查说明"><el-input v-model="form.self_check" type="textarea" :rows="4" placeholder="完成了什么、哪里还困难、下一步怎么做" /></el-form-item></el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" :loading="submitting" @click="submit">提交</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { checkinCaseTask, getMyCase } from '../../api/studentCases'
const detail = ref(null), loading = ref(false), notFound = ref(false), dialog = ref(false), submitting = ref(false)
const selectedTask = ref(null)
const form = reactive({ completion_rate: 0, self_check: '' })
const labels = { executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }
async function load() { loading.value = true; try { detail.value = await getMyCase() } catch (error) { if (error.response?.status === 404 || error.response?.status === 403) notFound.value = true } finally { loading.value = false } }
function openCheckin(task) { selectedTask.value = task; form.completion_rate = task.status === 'completed' ? 100 : 0; form.self_check = ''; dialog.value = true }
async function submit() { submitting.value = true; try { await checkinCaseTask(selectedTask.value.id, form); ElMessage.success('自查已提交'); dialog.value = false; await load() } finally { submitting.value = false } }
onMounted(load)
</script>

<style scoped>
.page { display: grid; gap: 24px; }
.hero { display: flex; justify-content: space-between; gap: 30px; padding: 30px; border-radius: 16px; color: #fff; background: linear-gradient(120deg, #173f5f, #20639b 58%, #3caea3); }
.hero p, .hero h1 { margin: 0 0 8px; }.hero h1 { font-size: 32px; }.target { min-width: 260px; padding-left: 28px; border-left: 1px solid rgba(255,255,255,.35); }.target small,.target strong { display: block; }.target strong { margin-top: 10px; font-size: 20px; }
.section-head h2 { margin-bottom: 6px; }.section-head p { margin: 0; color: #64748b; }
.task-list { display: grid; gap: 12px; }.task { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 18px 20px; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; }.task h3 { display: inline; margin-left: 10px; }.task p { color: #475569; }.task small { color: #64748b; }
.columns { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.goal,.review { display: flex; justify-content: space-between; gap: 16px; padding: 12px 0; border-bottom: 1px solid #edf2f7; }.review { flex-direction: column; }.review small { color: #64748b; }
@media (max-width: 800px) { .hero,.task { align-items: flex-start; flex-direction: column; }.target { padding: 20px 0 0; border-left: 0; border-top: 1px solid rgba(255,255,255,.35); }.columns { grid-template-columns: 1fr; } }
</style>
