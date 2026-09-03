<template>
  <view class="page">
    <view class="head">
      <text class="h1">生成月度评价</text>
      <text class="p">AI 将根据学生本月数据自动生成评价</text>
    </view>

    <view class="card">
      <text class="card-title">选择学生与月份</text>
      <view class="form">
        <view class="field">
          <text class="field-label">学生 <text class="required">*</text></text>
          <picker :range="studentNames" :value="studentIndex" @change="studentIndex = $event.detail.value">
            <view class="picker-box">
              <text class="picker-text">{{ studentNames[studentIndex] || '选择学生' }}</text>
              <text class="picker-arrow">▼</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">月份 <text class="required">*</text></text>
          <picker mode="date" fields="month" :value="monthLabel" @change="monthLabel = $event.detail.value">
            <view class="picker-box">
              <text class="picker-text">{{ monthLabel || '选择月份' }}</text>
              <text class="picker-arrow">▼</text>
            </view>
          </picker>
        </view>
      </view>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" @click="handleGenerate">
        {{ submitting ? '生成中...' : 'AI 生成评价' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { listClassStudents } from '../../api/classes'
import { generateMonthlyReport } from '../../api/monthlyReports'

const classId = ref(null)
const studentList = ref([])
const studentIndex = ref(0)
const submitting = ref(false)

const monthLabel = ref('')
const now = new Date()
monthLabel.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

const studentNames = computed(() => studentList.value.map(s => s.name))

onLoad((options) => {
  classId.value = Number(options.classId)
  loadStudents()
})

async function loadStudents() {
  try {
    studentList.value = await listClassStudents(classId.value)
  } catch (e) {
    studentList.value = []
  }
}

async function handleGenerate() {
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
    await generateMonthlyReport({
      student_id: student.id,
      class_id: classId.value,
      month_label: monthLabel.value,
    })
    uni.showToast({ title: '生成成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    // 错误已由 request 拦截器处理
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; margin-bottom: 14rpx; }

.form { display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: #4A4763; }
.required { color: #EF4444; }
.picker-box {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 18rpx 22rpx;
}
.picker-text { font-size: 28rpx; color: #1A1636; }
.picker-arrow { font-size: 20rpx; color: #A09CB5; }

.submit-bar {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid #E0E7E5;
}
.btn-submit {
  background: #1F4F55; color: #fff; border-radius: 8rpx;
  padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none;
}
.btn-submit::after { border: none; }
</style>
