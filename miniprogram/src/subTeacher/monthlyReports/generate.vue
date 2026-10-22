<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">填写月度评定</text>
      <text class="p">班主任填写德育总结、问题、计划；学科由对应老师填写</text>
    </view>

    <view class="card">
      <text class="card-title">选择学生与月份</text>
      <view class="form">
        <view class="field">
          <text class="field-label">学生 <text class="required">*</text></text>
          <picker :range="studentNames" :value="studentIndex" :disabled="!!targetStudentId" @change="studentIndex = $event.detail.value">
            <view class="picker-box">
              <text class="picker-text">{{ studentNames[studentIndex] || '选择学生' }}</text>
              <text class="picker-arrow">▼</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">月份 <text class="required">*</text></text>
          <picker mode="date" fields="month" :value="monthLabel" :disabled="!!targetStudentId" @change="monthLabel = $event.detail.value">
            <view class="picker-box">
              <text class="picker-text">{{ monthLabel || '选择月份' }}</text>
              <text class="picker-arrow">▼</text>
            </view>
          </picker>
        </view>
      </view>
    </view>

    <view class="card">
      <text class="card-title">{{ evaluationRole === 'head_teacher' ? '德育月度评定' : (evaluationRole === 'subject_teacher' || auth.role === 'subject_teacher' ? '学科月度评定' : '月度评定') }} <text class="required">*</text></text>
      <MonthlyReviewForm v-model="content" :limit="evaluationRole === 'head_teacher' ? 2400 : 600" :disabled="submitting || loadingContent || loadFailed" />
      <button v-if="loadFailed" size="mini" @click="loadStudents">加载失败，点击重试</button>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" :disabled="submitting || loadingContent || loadFailed" @click="handleCreate">
        {{ submitting ? '保存中...' : '保存评定' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { useAuthStore } from '../../stores/auth'
import MonthlyReviewForm from '../../components/MonthlyReviewForm.vue'
import { completeReview, reviewError } from '../../utils/monthlyReview'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { listClassStudents } from '../api/classes'
import { createMonthlyReport, listMonthlyReports, saveMonthlyEvaluation, updateMonthlyReport } from '../../api/monthlyReports'

const auth = useAuthStore()
const classId = ref(null)
const studentList = ref([])
const studentIndex = ref(0)
const submitting = ref(false)
const content = ref('')
const targetStudentId = ref(null)
const evaluationRole = ref('')
const loadingContent = ref(false)
const loadFailed = ref(false)

const monthLabel = ref('')
const now = new Date()
monthLabel.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

const studentNames = computed(() => studentList.value.map(s => s.name))

onLoad((options) => {
  classId.value = Number(options.classId)
  targetStudentId.value = Number(options.studentId) || null
  evaluationRole.value = options.evaluationRole || ''
  if (options.month) monthLabel.value = options.month
  loadStudents()
})

async function loadStudents() {
  loadingContent.value = true
  loadFailed.value = false
  try {
    studentList.value = await listClassStudents(classId.value)
    if (targetStudentId.value) {
      const index = studentList.value.findIndex(s => s.id === targetStudentId.value)
      if (index < 0) throw new Error('学生不在当前班级')
      studentIndex.value = index
      const existing = (await listMonthlyReports({ student_id: targetStudentId.value, class_id: classId.value, month_label: monthLabel.value }))[0]
      content.value = evaluationRole.value === 'head_teacher' ? existing?.final_content || '' : existing?.evaluations?.find(e => e.teacher_id === auth.user?.id && e.teacher_role === 'subject_teacher')?.content || ''
    }
  } catch (e) {
    studentList.value = []
    loadFailed.value = true
  } finally { loadingContent.value = false }
}

async function handleCreate() {
  if (submitting.value || loadingContent.value || loadFailed.value) return
  if (!completeReview(content.value)) {
    uni.showToast({ title: reviewError(content.value), icon: 'none' })
    return
  }
  if (!studentList.value.length) {
    uni.showToast({ title: '暂无学生', icon: 'none' })
    return
  }
  if (!monthLabel.value) {
    uni.showToast({ title: '请选择月份', icon: 'none' })
    return
  }

  const student = studentList.value[studentIndex.value]
  if (!student) return

  submitting.value = true
  try {
    const payload = {
      student_id: student.id,
      class_id: classId.value,
      month_label: monthLabel.value,
      final_content: content.value.trim(),
      ...(evaluationRole.value ? { evaluation_role: evaluationRole.value } : {}),
    }
    const existing = (await listMonthlyReports({ student_id: student.id, class_id: classId.value, month_label: monthLabel.value }))[0]
    const report = existing && evaluationRole.value === 'head_teacher'
      ? await updateMonthlyReport(existing.id, { final_content: payload.final_content })
      : existing && (evaluationRole.value === 'subject_teacher' || !existing.can_manage)
      ? await saveMonthlyEvaluation(existing.id, { content: payload.final_content })
      : await createMonthlyReport(payload)
    uni.showToast({ title: '评定已保存', icon: 'success' })
    uni.redirectTo({ url: `/subTeacher/monthlyReports/detail?id=${report.id}` })
  } catch (e) {
    // 错误已由 request 拦截器处理
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.manual-content { box-sizing: border-box; width: 100%; height: 480rpx; padding: 20rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; background: #F7F8FA; color: var(--mp-ink); font-size: 28rpx; line-height: 1.7; }
.char-count { display: block; margin-top: 12rpx; text-align: right; font-size: 24rpx; color: var(--mp-muted); }
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); display: block; margin-bottom: 14rpx; }

.form { display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: var(--mp-body); }
.required { color: #A33E39; }
.picker-box {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1rpx solid #C6D0DE; border-radius: 8rpx;
  padding: 18rpx 22rpx;
}
.picker-text { font-size: 28rpx; color: var(--mp-ink); }
.picker-arrow { font-size: 24rpx; color: var(--mp-muted); }

.submit-bar {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid var(--mp-line);
}
.btn-submit {
  background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none;
}
.btn-submit::after { border: none; }
</style>
