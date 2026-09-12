<template>
  <section v-loading="loading" class="page student-case-page">
    <div v-if="detail" class="overview-banner">
      <div class="banner-main">
        <div class="banner-tag-row">
          <span class="sub-badge">高三 · 我的学业成长主线</span>
          <span class="version-chip">第 {{ detail.version }} 版 · {{ labels[detail.status] || detail.status }}</span>
        </div>
        <h1>一生一案个性化成长档案</h1>
        <p class="banner-desc">遵循阶段方案与突破目标，按节奏完成每日微任务与自我检查。</p>
      </div>
      <div class="banner-target">
        <span class="target-title">我的升学目标</span>
        <strong class="target-content">{{ detail.admission_target || '待老师确认' }}</strong>
      </div>
    </div>

    <el-alert v-if="notFound" title="班主任尚未发布你的正式方案，请稍后查阅或咨询老师" type="info" :closable="false" show-icon />

    <template v-if="detail">
      <div class="section-container">
        <div class="section-head">
          <div>
            <h2>近期推进任务</h2>
            <p>如实记录执行进展与自查心得，不以表面数字为目的。</p>
          </div>
        </div>

        <div v-if="detail.tasks.length" class="task-grid">
          <article v-for="task in detail.tasks" :key="task.id" class="task-card">
            <div class="task-body">
              <div class="task-title-row">
                <span class="subject-tag">{{ task.subject || '综合' }}</span>
                <span class="task-name">{{ task.title }}</span>
              </div>
              <p class="task-desc">{{ task.description }}</p>
              <div class="task-meta">
                <span>周期：{{ task.starts_on }} 至 {{ task.due_on }}</span>
                <span class="task-status-badge" :class="`is-${task.status}`">状态：{{ task.status }}</span>
              </div>
            </div>
            <div class="task-action">
              <el-button type="primary" plain @click="openCheckin(task)">
                提交自查
              </el-button>
            </div>
          </article>
        </div>
        <el-empty v-else description="当前暂无待执行任务" :image-size="80" />
      </div>

      <div class="columns-grid">
        <el-card shadow="never" class="info-panel">
          <template #header>
            <div class="panel-header">
              <strong>阶段性目标</strong>
            </div>
          </template>
          <div v-for="goal in detail.goals" :key="goal.id" class="goal-item">
            <span class="goal-title">{{ goal.title }}</span>
            <span class="goal-val">{{ goal.target_value ?? '定性目标' }}</span>
          </div>
          <el-empty v-if="!detail.goals.length" description="暂无阶段目标" :image-size="60" />
        </el-card>

        <el-card shadow="never" class="info-panel">
          <template #header>
            <div class="panel-header">
              <strong>教师复盘建议</strong>
            </div>
          </template>
          <div v-for="review in detail.reviews.slice(0, 5)" :key="review.id" class="review-item">
            <span class="review-problem">{{ review.problem || '执行情况正常' }}</span>
            <small class="review-action">{{ review.corrective_action }}</small>
          </div>
          <el-empty v-if="!detail.reviews.length" description="暂无复盘反馈" :image-size="60" />
        </el-card>
      </div>
    </template>

    <!-- 自查弹窗 -->
    <el-dialog v-model="dialog" title="任务完成自查反馈" width="480px">
      <el-form label-position="top">
        <el-form-item label="任务完成度预估 (%)">
          <el-slider v-model="form.completion_rate" show-input />
        </el-form-item>
        <el-form-item label="自查总结与疑难点">
          <el-input
            v-model="form.self_check"
            type="textarea"
            :rows="4"
            placeholder="请如实描述：完成了哪些内容、哪些题目或知识点仍有疑问、下一步调整计划"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交自查</el-button>
      </template>
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

async function load() {
  loading.value = true
  try {
    detail.value = await getMyCase()
  } catch (error) {
    if (error.response?.status === 404 || error.response?.status === 403) notFound.value = true
  } finally {
    loading.value = false
  }
}

function openCheckin(task) {
  selectedTask.value = task
  form.completion_rate = task.status === 'completed' ? 100 : 0
  form.self_check = ''
  dialog.value = true
}

async function submit() {
  submitting.value = true
  try {
    await checkinCaseTask(selectedTask.value.id, form)
    ElMessage.success('自查已提交')
    dialog.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.student-case-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-banner {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  background: var(--ink);
  border-radius: var(--radius);
  color: #ffffff;
  padding: 28px 32px;
  border: 1px solid var(--side-line);
  gap: 24px;
}

.banner-main {
  flex: 1;
}

.banner-tag-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.sub-badge {
  font-size: 11px;
  background: var(--side-line);
  color: #94a3b8;
  padding: 2px 8px;
  border-radius: 6px;
}

.version-chip {
  font-size: 11px;
  background: rgba(37, 99, 235, 0.2);
  color: #60a5fa;
  padding: 2px 8px;
  border-radius: 6px;
}

.banner-main h1 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.banner-desc {
  margin: 0;
  font-size: 13.5px;
  color: #94a3b8;
  max-width: 60ch;
  line-height: 1.5;
}

.banner-target {
  min-width: 240px;
  background: var(--side-line);
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.target-title {
  font-size: 11.5px;
  color: #94a3b8;
}

.target-content {
  margin-top: 6px;
  font-size: 16px;
  color: #ffffff;
  font-weight: 600;
  line-height: 1.4;
}

.section-head {
  margin-bottom: 14px;
}

.section-head h2 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.section-head p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.task-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
}

.task-body {
  flex: 1;
}

.task-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subject-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 6px;
  border-radius: 6px;
}

.task-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.task-desc {
  margin: 6px 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.task-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #64748b;
}

.task-status-badge {
  font-weight: 500;
}

.columns-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 6px;
}

.info-panel {
  border-radius: var(--radius);
}

.panel-header strong {
  font-size: 14px;
  color: var(--ink);
}

.goal-item, .review-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
}

.goal-item:last-child, .review-item:last-child {
  border-bottom: none;
}

.goal-title {
  font-size: 13.5px;
  color: #334155;
}

.goal-val {
  font-size: 13px;
  color: #2f5bff;
  font-weight: 600;
}

.review-item {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.review-problem {
  font-size: 13.5px;
  color: var(--ink);
  font-weight: 500;
}

.review-action {
  font-size: 12px;
  color: #64748b;
}

@media (max-width: 800px) {
  .overview-banner {
    flex-direction: column;
    padding: 20px;
  }
  .banner-target {
    min-width: 100%;
  }
  .task-card {
    flex-direction: column;
    align-items: flex-start;
  }
  .columns-grid {
    grid-template-columns: 1fr;
  }
}
</style>
