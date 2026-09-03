<template>
  <view class="page">
    <view class="head">
      <text class="h1">录入周测成绩</text>
      <text class="p">{{ className }}</text>
    </view>

    <!-- 考试信息 -->
    <view class="card">
      <text class="card-title">考试信息</text>
      <view class="form">
        <view class="field">
          <text class="field-label">科目 <text class="required">*</text></text>
          <picker :range="subjectOptions" :value="subjectIndex" @change="subjectIndex = $event.detail.value">
            <view class="picker-box">
              <text class="picker-text">{{ subjectOptions[subjectIndex] || '选择科目' }}</text>
              <text class="picker-arrow">▼</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">考试名称</text>
          <input v-model="form.exam_name" placeholder="如：第五周周测" class="input" />
        </view>
        <view class="field">
          <text class="field-label">考试日期 <text class="required">*</text></text>
          <picker mode="date" :value="form.exam_date" @change="form.exam_date = $event.detail.value">
            <view class="picker-box">
              <text class="picker-text">{{ form.exam_date || '选择日期' }}</text>
              <text class="picker-arrow">▼</text>
            </view>
          </picker>
        </view>
        <view class="field">
          <text class="field-label">满分 <text class="required">*</text></text>
          <input v-model="form.max_score" type="digit" placeholder="如：100" class="input" />
        </view>
      </view>
    </view>

    <!-- 学生成绩列表 -->
    <view class="card">
      <view class="card-header-row">
        <text class="card-title">学生成绩</text>
        <text class="student-count">共{{ studentList.length }}人</text>
      </view>
      <view v-if="loadingStudents" class="loading-bar">
        <text class="loading-text">加载学生列表...</text>
      </view>
      <EmptyState v-else-if="!studentList.length" title="暂无学生" desc="请先在班级中添加学生" icon="👤" />
      <view v-else class="student-list">
        <view v-for="(stu, idx) in studentList" :key="stu.id" class="student-row" :class="{ 'has-border': idx > 0 }">
          <view class="student-info">
            <text class="student-name">{{ stu.name }}</text>
            <text class="student-id">学号{{ stu.username }}</text>
          </view>
          <view class="student-score">
            <input
              v-model="scoreMap[stu.id]"
              type="digit"
              placeholder="分数"
              class="score-input"
              :class="{ 'has-value': scoreMap[stu.id] }"
            />
            <input
              v-model="rankMap[stu.id]"
              type="number"
              placeholder="名次"
              class="rank-input"
            />
          </view>
        </view>
      </view>
    </view>

    <!-- 提交按钮 -->
    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" @click="handleSubmit">
        {{ submitting ? '提交中...' : '保存成绩' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { listClassStudents } from '../../api/classes'
import { batchCreateWeeklyScores } from '../../api/weeklyScores'
import EmptyState from '../../components/EmptyState.vue'

const classId = ref(null)
const className = ref('')
const loadingStudents = ref(false)
const submitting = ref(false)
const studentList = ref([])
const scoreMap = reactive({})
const rankMap = reactive({})

const subjectOptions = ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
const subjectIndex = ref(0)

const form = reactive({
  exam_name: '',
  exam_date: '',
  max_score: '100',
})

onLoad((options) => {
  classId.value = Number(options.classId)
  className.value = decodeURIComponent(options.className || '')
  // 默认日期为今天
  const now = new Date()
  form.exam_date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  loadStudents()
})

async function loadStudents() {
  loadingStudents.value = true
  try {
    studentList.value = await listClassStudents(classId.value)
  } catch (e) {
    studentList.value = []
  } finally {
    loadingStudents.value = false
  }
}

function validate() {
  if (!subjectOptions[subjectIndex.value]) {
    uni.showToast({ title: '请选择科目', icon: 'none' })
    return false
  }
  if (!form.exam_date) {
    uni.showToast({ title: '请选择考试日期', icon: 'none' })
    return false
  }
  const maxScore = parseFloat(form.max_score)
  if (!maxScore || maxScore <= 0) {
    uni.showToast({ title: '请填写满分', icon: 'none' })
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return

  // 构建批量数据
  const records = []
  for (const stu of studentList.value) {
    const score = scoreMap[stu.id]
    if (score !== undefined && score !== '') {
      records.push({
        student_id: stu.id,
        score: parseFloat(score),
        rank_in_class: rankMap[stu.id] ? parseInt(rankMap[stu.id]) : null,
      })
    }
  }

  if (!records.length) {
    uni.showToast({ title: '请至少录入一名学生的成绩', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    await batchCreateWeeklyScores({
      class_id: classId.value,
      subject: subjectOptions[subjectIndex.value],
      exam_date: form.exam_date,
      exam_name: form.exam_name || `${subjectOptions[subjectIndex.value]}周测`,
      max_score: parseFloat(form.max_score),
      records,
    })
    uni.showToast({ title: '保存成功', icon: 'success' })
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
.card-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14rpx; }
.student-count { font-size: 22rpx; color: #A09CB5; }

.form { display: flex; flex-direction: column; gap: 16rpx; }
.field { display: flex; flex-direction: column; gap: 6rpx; }
.field-label { font-size: 24rpx; font-weight: 500; color: #4A4763; }
.required { color: #EF4444; }
.input {
  border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 18rpx 22rpx; font-size: 28rpx; background: #fff;
}
.picker-box {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 18rpx 22rpx;
}
.picker-text { font-size: 28rpx; color: #1A1636; }
.picker-arrow { font-size: 20rpx; color: #A09CB5; }

.loading-bar { text-align: center; padding: 32rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.student-row {
  padding: 16rpx 0; display: flex; align-items: center; justify-content: space-between;
}
.student-row.has-border { border-top: 2rpx solid #F0EFFC; }
.student-info { flex: 1; }
.student-name { font-size: 26rpx; font-weight: 600; color: #1A1636; display: block; }
.student-id { font-size: 20rpx; color: #A09CB5; display: block; margin-top: 4rpx; }
.student-score { display: flex; gap: 12rpx; }
.score-input {
  width: 120rpx; border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 12rpx 14rpx; font-size: 28rpx; text-align: center; background: #FAF9F7;
}
.score-input.has-value { background: #fff; border-color: #1F4F55; }
.rank-input {
  width: 100rpx; border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 12rpx 14rpx; font-size: 28rpx; text-align: center; background: #FAF9F7;
}

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
