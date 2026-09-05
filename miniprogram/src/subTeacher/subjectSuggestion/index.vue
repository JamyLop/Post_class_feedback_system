<template>
  <view class="page">
    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="detail">
      <view class="header-card">
        <text class="h1">{{ detail.student_name || `学生 #${detail.student_id}` }}</text>
        <text class="meta">{{ detail.class_name }} · 第{{ detail.version }}版</text>
      </view>

      <view class="section">
        <text class="section-h">学科方案</text>
        <view v-if="!detail.subject_plans.length" class="empty-text">暂无学科方案</view>
        <view v-for="plan in detail.subject_plans" :key="plan.id" class="plan-card">
          <text class="subject-chip">{{ plan.subject }}</text>
          <view class="field"><text class="dt">问题定位</text><text class="dd">{{ plan.problem_location || '—' }}</text></view>
          <view class="field"><text class="dt">原因剖析</text><text class="dd">{{ plan.cause_analysis || '—' }}</text></view>
          <view class="field"><text class="dt">奋斗目标</text><text class="dd">{{ plan.struggle_goal || '—' }}</text></view>
          <view class="field"><text class="dt">高考要求</text><text class="dd">{{ plan.gaokao_requirement || '—' }}</text></view>
          <view class="field"><text class="dt">具体强化</text><text class="dd">{{ plan.reinforcement || '—' }}</text></view>
        </view>
      </view>

      <view class="section">
        <view class="section-head-row">
          <text class="section-h">我的学科建议</text>
          <text class="add-link" @click="showForm = true">+ 新建</text>
        </view>
        <view v-if="!suggestions.length" class="empty-text">暂无建议记录</view>
        <view v-for="s in suggestions" :key="s.id" class="suggestion-card">
          <view class="sug-head">
            <text class="subject-chip">{{ s.subject }}</text>
            <text class="sug-time">{{ (s.created_at || '').slice(0, 10) }}</text>
          </view>
          <text class="sug-body">{{ s.content }}</text>
        </view>
      </view>

      <view v-if="showForm" class="modal-mask" @click.self="showForm = false">
        <view class="modal-card">
          <text class="modal-title">提交学科建议</text>

          <view class="form-item">
            <text class="form-label">所属学科</text>
            <picker :range="mySubjects" @change="onSubjectPick">
              <view class="picker-box">
                <text>{{ form.subject || '请选择学科' }}</text>
                <text class="picker-arrow">›</text>
              </view>
            </picker>
          </view>

          <view class="form-item">
            <text class="form-label">建议内容</text>
            <textarea
              v-model="form.content"
              class="form-textarea"
              placeholder="请输入对学科方案的修改建议"
              maxlength="1000"
            />
          </view>

          <view class="form-item">
            <text class="form-label">参考分数（可选）</text>
            <input v-model="form.reference_score" type="number" class="form-input" placeholder="如：120" />
          </view>

          <view class="modal-actions">
            <view class="modal-btn cancel" @click="showForm = false"><text>取消</text></view>
            <view class="modal-btn confirm" :class="{ disabled: submitting }" @click="doSubmit">
              <text>{{ submitting ? '提交中...' : '提交' }}</text>
            </view>
          </view>
        </view>
      </view>
    </template>
    <EmptyState v-else title="档案不存在" desc="可能已被移除或无权查看" icon="📄" />
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStudentCase, listSubjectSuggestions, createSubjectSuggestion } from '../../api/studentCases'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)
const suggestions = ref([])
const showForm = ref(false)
const submitting = ref(false)
const form = ref({ subject: '', content: '', reference_score: '' })

const mySubjects = computed(() => {
  const plans = detail.value?.subject_plans || []
  return plans.map(p => p.subject)
})

function caseId() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]
  return cur.options?.id || cur.$page?.options?.id
}

function onSubjectPick(e) {
  form.value.subject = mySubjects.value[e.detail.value]
}

async function load() {
  loading.value = true
  try {
    const id = caseId()
    if (!id) throw new Error('缺少 case id')
    const [d, s] = await Promise.all([
      getStudentCase(id),
      listSubjectSuggestions(id).catch(() => []),
    ])
    detail.value = d
    suggestions.value = Array.isArray(s) ? s : []
  } catch (e) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally { loading.value = false }
}

async function doSubmit() {
  if (submitting.value) return
  if (!form.value.subject) {
    uni.showToast({ title: '请选择学科', icon: 'none' }); return
  }
  if (!form.value.content.trim()) {
    uni.showToast({ title: '请填写建议内容', icon: 'none' }); return
  }
  submitting.value = true
  try {
    const id = caseId()
    const payload = { subject: form.value.subject, content: form.value.content.trim() }
    if (form.value.reference_score) payload.reference_score = Number(form.value.reference_score)
    await createSubjectSuggestion(id, payload)
    uni.showToast({ title: '提交成功', icon: 'success' })
    showForm.value = false
    form.value = { subject: '', content: '', reference_score: '' }
    const s = await listSubjectSuggestions(id).catch(() => [])
    suggestions.value = Array.isArray(s) ? s : []
  } catch (e) {
    uni.showToast({ title: e.message || '提交失败', icon: 'none' })
  } finally { submitting.value = false }
}

onShow(() => load())
</script>

<style scoped>
.page { padding: 24rpx 20rpx 48rpx; display: flex; flex-direction: column; gap: 18rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.header-card {
  background: #fff; border-radius: 20rpx; padding: 28rpx;
  box-shadow: 0 2rpx 16rpx rgba(107,92,231,0.06);
}
.h1 { font-size: 32rpx; font-weight: 700; color: #1A1636; }
.meta { font-size: 22rpx; color: #A09CB5; display: block; margin-top: 8rpx; }

.section { display: flex; flex-direction: column; gap: 12rpx; }
.section-h { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.section-head-row { display: flex; justify-content: space-between; align-items: center; }
.add-link { font-size: 24rpx; color: #6B5CE7; font-weight: 500; }
.empty-text { text-align: center; color: #A09CB5; padding: 28rpx; font-size: 24rpx; }

.plan-card, .suggestion-card {
  background: #FAF9F7; border-radius: 14rpx; padding: 20rpx;
  display: flex; flex-direction: column; gap: 10rpx;
}
.subject-chip {
  font-size: 22rpx; font-weight: 600; color: #6B5CE7;
  background: #EEEDFD; padding: 6rpx 16rpx; border-radius: 16rpx;
  display: inline-block;
}

.field { display: flex; flex-direction: column; gap: 4rpx; margin-top: 8rpx; }
.dt { font-size: 22rpx; color: #8E8B9E; }
.dd { font-size: 24rpx; color: #4A4763; line-height: 1.6; white-space: pre-wrap; }

.sug-head { display: flex; justify-content: space-between; align-items: center; }
.sug-time { font-size: 22rpx; color: #A09CB5; }
.sug-body { font-size: 24rpx; color: #4A4763; line-height: 1.6; white-space: pre-wrap; margin-top: 6rpx; }

.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.45); z-index: 100;
  display: flex; align-items: center; justify-content: center;
  padding: 40rpx;
}
.modal-card {
  background: #fff; border-radius: 20rpx; padding: 32rpx;
  width: 100%; display: flex; flex-direction: column; gap: 24rpx;
}
.modal-title { font-size: 30rpx; font-weight: 700; color: #1A1636; }

.form-item { display: flex; flex-direction: column; gap: 8rpx; }
.form-label { font-size: 24rpx; font-weight: 600; color: #4A4763; }
.form-input {
  font-size: 26rpx; padding: 18rpx; border-radius: 10rpx;
  border: 1rpx solid #E0E7E5; background: #FAF9F7;
}
.form-textarea {
  font-size: 26rpx; padding: 18rpx; border-radius: 10rpx;
  border: 1rpx solid #E0E7E5; background: #FAF9F7;
  min-height: 160rpx; width: 100%; box-sizing: border-box;
}
.picker-box {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 26rpx; padding: 18rpx; border-radius: 10rpx;
  border: 1rpx solid #E0E7E5; background: #FAF9F7;
  color: #4A4763;
}
.picker-arrow { color: #A09CB5; font-size: 28rpx; }

.modal-actions { display: flex; gap: 16rpx; margin-top: 8rpx; }
.modal-btn {
  flex: 1; text-align: center; padding: 20rpx; border-radius: 12rpx;
  font-size: 28rpx; font-weight: 600;
}
.modal-btn.cancel { background: #F5F3EF; color: #4A4763; }
.modal-btn.confirm { background: #6B5CE7; color: #fff; }
.modal-btn.disabled { opacity: 0.5; }
</style>
