<template>
  <view class="page">
    <WorkspaceLink />
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view class="tabs">
        <view class="tab-bar">
          <text class="tab" :class="{ active: tab==='basic' }" @click="tab='basic'">总案信息</text>
          <text class="tab" :class="{ active: tab==='subjects' }" @click="tab='subjects'">学科方案</text>
        </view>

        <view v-if="tab==='basic'" class="tab-panel">
          <view class="form">
            <view class="field">
              <text class="label">总体问题</text>
              <textarea v-model="basicForm.overall_problem" placeholder="学生当前面临的核心问题" class="textarea" />
            </view>
            <view class="field">
              <text class="label">升学目标</text>
              <textarea v-model="basicForm.admission_target" placeholder="目标院校与专业方向" class="textarea" />
            </view>
            <view class="field">
              <text class="label">当前阶段说明</text>
              <textarea v-model="basicForm.current_summary" placeholder="当前执行状态说明（可选）" class="textarea" />
            </view>
          </view>
          <button class="btn-primary" :loading="saving" :disabled="saving" @click="saveBasic">保存</button>
        </view>

        <view v-if="tab==='subjects'" class="tab-panel">
          <view v-if="!plans.length" class="empty-text">暂无学科方案，请先保存总案信息后新增</view>
          <view v-for="plan in plans" :key="plan.subject" class="plan-card">
            <view class="plan-head">
              <text class="subject-chip">{{ plan.subject }}</text>
              <text class="edit-link" @click="editPlan(plan)">编辑</text>
            </view>
            <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
            <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
          </view>
          <picker :range="availableSubjects" @change="onAddPlan">
            <view class="add-btn"><text class="add-link">+ 新增学科方案</text></view>
          </picker>
        </view>
      </view>

      <view v-if="showPlanForm" class="modal-mask" @click.self="showPlanForm=false">
        <view class="modal">
          <view class="modal-header">
            <text class="modal-title">{{ editingPlan.subject }} 方案</text>
            <text class="modal-close" @click="showPlanForm=false">✕</text>
          </view>
          <view class="form">
            <view class="field">
              <text class="label">问题定位</text>
              <textarea v-model="planForm.problem_location" class="textarea" placeholder="该学科核心问题" />
            </view>
            <view class="field">
              <text class="label">原因剖析</text>
              <textarea v-model="planForm.cause_analysis" class="textarea" placeholder="问题成因" />
            </view>
            <view class="field">
              <text class="label">奋斗目标</text>
              <textarea v-model="planForm.struggle_goal" class="textarea" placeholder="目标分数/排名" />
            </view>
            <view class="field">
              <text class="label">高考要求</text>
              <textarea v-model="planForm.gaokao_requirement" class="textarea" placeholder="高考要求" />
            </view>
            <view class="field">
              <text class="label">具体强化</text>
              <textarea v-model="planForm.reinforcement" class="textarea" placeholder="具体提分措施" />
            </view>
          </view>
          <view class="modal-btns">
            <button class="btn-outline" @click="showPlanForm=false">取消</button>
            <button class="btn-primary" :loading="savingPlan" :disabled="savingPlan" @click="savePlan">保存</button>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, updateStudentCase, upsertSubjectPlan } from '../../api/studentCases'

const loading = ref(false)
const saving = ref(false)
const savingPlan = ref(false)
const tab = ref('basic')
const detail = ref(null)
const showPlanForm = ref(false)
const editingPlan = ref({ subject: '' })

const basicForm = reactive({ overall_problem: '', admission_target: '', current_summary: '' })
const planForm = reactive({ problem_location: '', cause_analysis: '', struggle_goal: '', gaokao_requirement: '', reinforcement: '' })

const plans = computed(() => detail.value?.subject_plans || [])
const allSubjects = ['语文','数学','英语','物理','化学','生物','政治','历史','地理']
const availableSubjects = computed(() => {
  const used = new Set(plans.value.map(p => p.subject))
  return allSubjects.filter(s => !used.has(s))
})

function getCaseId() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options?.caseId || cur.options?.id || cur.$page?.options?.caseId || cur.$page?.options?.id
}

async function load() {
  loading.value = true
  try {
    const id = getCaseId()
    if (!id) throw new Error('缺少 caseId')
    detail.value = await getStudentCase(id)
    basicForm.overall_problem = detail.value.overall_problem || ''
    basicForm.admission_target = detail.value.admission_target || ''
    basicForm.current_summary = detail.value.current_summary || ''
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1]
    if (cur.options?.tab === 'subjects') {
      tab.value = 'subjects'
      if (cur.options?.subject) {
        const existing = plans.value.find(p => p.subject === decodeURIComponent(cur.options.subject))
        if (existing) editPlan(existing)
        else onAddPlan({ detail: { value: availableSubjects.value.indexOf(decodeURIComponent(cur.options.subject)) } })
      }
    }
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loading.value = false }
}

async function saveBasic() {
  saving.value = true
  try {
    await updateStudentCase(getCaseId(), {
      overall_problem: basicForm.overall_problem,
      admission_target: basicForm.admission_target,
      current_summary: basicForm.current_summary,
    })
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  } finally { saving.value = false }
}

function editPlan(plan) {
  editingPlan.value = { subject: plan.subject }
  planForm.problem_location = plan.problem_location || ''
  planForm.cause_analysis = plan.cause_analysis || ''
  planForm.struggle_goal = plan.struggle_goal || ''
  planForm.gaokao_requirement = plan.gaokao_requirement || ''
  planForm.reinforcement = plan.reinforcement || ''
  showPlanForm.value = true
}

function onAddPlan(e) {
  const subject = availableSubjects.value[e.detail.value]
  if (!subject) return
  editingPlan.value = { subject }
  planForm.problem_location = ''
  planForm.cause_analysis = ''
  planForm.struggle_goal = ''
  planForm.gaokao_requirement = ''
  planForm.reinforcement = ''
  showPlanForm.value = true
}

async function savePlan() {
  savingPlan.value = true
  try {
    await upsertSubjectPlan(getCaseId(), editingPlan.value.subject, {
      subject: editingPlan.value.subject,
      teacher_id: detail.value.owner_teacher_id,
      problem_location: planForm.problem_location,
      cause_analysis: planForm.cause_analysis,
      struggle_goal: planForm.struggle_goal,
      gaokao_requirement: planForm.gaokao_requirement,
      reinforcement: planForm.reinforcement,
    })
    showPlanForm.value = false
    uni.showToast({ title: '已保存', icon: 'success' })
    detail.value = await getStudentCase(getCaseId())
  } catch (e) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  } finally { savingPlan.value = false }
}

onShow(() => load())

</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 16rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.tabs {
  background: #fff;
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: none;
}
.tab-bar { display: flex; border-bottom: 2rpx solid var(--mp-soft); }
.tab {
  flex: 1; text-align: center; padding: 22rpx 0;
  font-size: 26rpx; color: var(--mp-muted);
  border-bottom: 4rpx solid transparent;
}
.tab.active { color: var(--mp-primary); border-bottom-color: var(--mp-primary); font-weight: 600; }
.tab-panel { padding: 24rpx; display: flex; flex-direction: column; gap: 16rpx; }

.form { display: flex; flex-direction: column; gap: 14rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.label { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.textarea {
  border: 2rpx solid var(--mp-line);
  border-radius: 14rpx;
  padding: 18rpx 20rpx;
  font-size: 26rpx;
  min-height: 120rpx;
  background: #fff;
}
.empty-text { text-align: center; color: var(--mp-muted); padding: 28rpx; font-size: 24rpx; }

.plan-card {
  background: #F7F8FA;
  border-radius: 14rpx;
  padding: 18rpx;
  display: flex; flex-direction: column; gap: 8rpx;
}
.plan-head { display: flex; justify-content: space-between; align-items: center; }
.subject-chip {
  font-size: 24rpx; font-weight: 600;
  color: var(--mp-primary); background: var(--mp-soft);
  padding: 6rpx 16rpx; border-radius: 16rpx;
}
.edit-link { font-size: 24rpx; color: var(--mp-primary); }
.field { display: flex; flex-direction: column; gap: 4rpx; margin-top: 4rpx; }
.dt { font-size: 24rpx; color: var(--mp-muted); }
.dd { font-size: 24rpx; color: var(--mp-body); line-height: 1.6; white-space: pre-wrap; }
.add-btn { text-align: center; padding: 16rpx; }
.add-link { font-size: 26rpx; color: var(--mp-primary); font-weight: 500; }

.btn-primary {
  background: var(--mp-primary);
  color: #fff;
  border-radius: 14rpx;
  padding: 22rpx 0;
  font-size: 28rpx;
  font-weight: 600;
  border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  background: #fff;
  color: var(--mp-primary);
  border: 2rpx solid #B8C6D8;
  border-radius: 14rpx;
  padding: 22rpx 0;
  font-size: 28rpx;
}
.btn-outline::after { border: none; }

.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(26,22,54,0.45);
  display: flex; align-items: flex-end; z-index: 999;
}
.modal {
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 28rpx;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 16rpx;
}
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.modal-close { font-size: 28rpx; color: var(--mp-muted); padding: 8rpx; }
.modal-btns { display: flex; gap: 14rpx; margin-top: 8rpx; }
.modal-btns button { flex: 1; }
</style>

<style scoped src="../../styles/details.css"></style>
