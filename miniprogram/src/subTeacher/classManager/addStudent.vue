<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">新建学生</text>
      <text class="p">在 {{ className }} 中添加学生</text>
    </view>

    <view class="hint-card">
      <text class="hint-text">仅需录入学生信息，学号规则：Y/U(初中Y/高中U)+年级+年份后两位+入学月份+班号+位号，如 Y326090101</text>
    </view>

    <view class="card">
      <text class="card-title">学生信息</text>
      <view class="form">
        <view class="field">
          <text class="field-label">姓名 <text class="required">*</text></text>
          <input v-model="form.name" placeholder="请输入学生姓名" class="input" />
        </view>
        <view class="field">
          <text class="field-label">性别</text>
          <view class="radio-group">
            <view
              v-for="g in genderOptions"
              :key="g"
              class="radio-item"
              :class="{ active: form.gender === g }"
              @click="form.gender = form.gender === g ? '' : g"
            >
              <text class="radio-label">{{ g }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">民族</text>
          <input v-model="form.ethnicity" placeholder="例如：汉族" class="input" />
        </view>
        <view class="field">
          <text class="field-label">年级</text>
          <input v-model="form.grade" placeholder="例如：高三" class="input" />
        </view>
        <view class="field">
          <text class="field-label">生源地学校</text>
          <input v-model="form.source_school" placeholder="填写学生原就读学校" class="input" />
        </view>
        <view class="field">
          <text class="field-label">了解渠道</text>
          <input v-model="form.channel" placeholder="选填，例如：转介绍 / 线上咨询" class="input" />
        </view>
        <view class="field">
          <text class="field-label">咨询老师（选填）</text>
          <picker :range="consultantOptions" range-key="label" :value="consultantIndex" @change="onConsultantChange">
            <view class="input picker-input">
              <text>{{ consultantLabel }}</text>
              <text class="picker-arrow">⌄</text>
            </view>
          </picker>
        </view>
        <view class="field-row">
          <view class="field half">
            <text class="field-label">入学月份 <text class="required">*</text></text>
            <picker :range="monthOptions" :value="monthIndex" @change="onMonthChange">
              <view class="input picker-input">
                <text>{{ form.enrollment_month }} 月</text>
                <text class="picker-arrow">⌄</text>
              </view>
            </picker>
          </view>
          <view class="field half">
            <text class="field-label">班级位号 <text class="required">*</text></text>
            <picker :range="seatOptions" :value="seatIndex" @change="onSeatChange">
              <view class="input picker-input">
                <text>{{ form.seat_number }} 号</text>
                <text class="picker-arrow">⌄</text>
              </view>
            </picker>
          </view>
        </view>
      </view>
    </view>

    <view class="hint-card">
      <text class="hint-text">* 学生账号将自动生成，初始密码为 123456</text>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" :disabled="submitting" @click="handleSubmit">
        {{ submitting ? '创建中...' : '新建并加入班级' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { createAndEnrollStudent, getClass, listUsers } from '../../api/classes'

const classId = ref(null)
const className = ref('')
const submitting = ref(false)
const loadingMeta = ref(false)

const genderOptions = ['男', '女']

const form = reactive({
  name: '',
  gender: '',
  ethnicity: '',
  grade: '',
  source_school: '',
  channel: '',
  consultant_id: null,
  enrollment_month: 7,
  seat_number: 1,
})

const consultantOptions = ref([{ id: null, label: '不选择' }])
const consultantIndex = computed(() => {
  const idx = consultantOptions.value.findIndex((c) => c.id === form.consultant_id)
  return idx >= 0 ? idx : 0
})
const consultantLabel = computed(() => consultantOptions.value[consultantIndex.value]?.label || '不选择')

const monthOptions = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
const monthIndex = computed(() => (form.enrollment_month || 7) - 1)
const seatOptions = Array.from({ length: 99 }, (_, i) => `${i + 1}号`)
const seatIndex = computed(() => (form.seat_number || 1) - 1)

function onConsultantChange(e) {
  const item = consultantOptions.value[Number(e.detail.value)]
  form.consultant_id = item?.id || null
}
function onMonthChange(e) {
  form.enrollment_month = Number(e.detail.value) + 1
}
function onSeatChange(e) {
  form.seat_number = Number(e.detail.value) + 1
}

onLoad((options) => {
  classId.value = Number(options.classId)
  className.value = decodeURIComponent(options.className || '')
})

onMounted(loadMeta)

async function loadMeta() {
  loadingMeta.value = true
  try {
    // 预填年级默认值（与网页端一致：跟随班级年级）
    try {
      if (classId.value) {
        const cls = await getClass(classId.value)
        if (cls?.grade && !form.grade) form.grade = cls.grade
      }
    } catch (_) {}
    // 咨询老师选填：班主任可只读查询 teacher / consultant 名单
    try {
      const [teachers, consultants] = await Promise.all([
        listUsers('teacher', '').catch(() => []),
        listUsers('consultant', '').catch(() => []),
      ])
      const all = [...(teachers || []), ...(consultants || [])]
      consultantOptions.value = [
        { id: null, label: '不选择' },
        ...all.map((u) => ({ id: u.id, label: `${u.name}（${u.username}）` })),
      ]
    } catch (_) {}
  } finally {
    loadingMeta.value = false
  }
}

function validate() {
  if (!form.name.trim()) {
    uni.showToast({ title: '请填写学生姓名', icon: 'none' })
    return false
  }
  if (!form.enrollment_month || !form.seat_number) {
    uni.showToast({ title: '请填写入学月份和班级位号', icon: 'none' })
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    await createAndEnrollStudent(classId.value, {
      name: form.name.trim(),
      gender: form.gender || '',
      ethnicity: form.ethnicity.trim(),
      grade: form.grade.trim(),
      source_school: form.source_school.trim(),
      channel: form.channel.trim(),
      consultant_id: form.consultant_id || null,
      enrollment_month: form.enrollment_month,
      seat_number: form.seat_number,
    })
    uni.showToast({ title: '创建成功，账号已自动生成', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
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
.field-row { display: flex; gap: 16rpx; }
.field-row .half { flex: 1; }
.field-label { font-size: 24rpx; font-weight: 500; color: var(--mp-body); }
.required { color: #A33E39; }
.input {
  border: 1rpx solid #C6D0DE; border-radius: 8rpx;
  padding: 18rpx 22rpx; font-size: 28rpx; background: #fff;
}
.picker-input { display: flex; align-items: center; justify-content: space-between; }
.picker-arrow { color: var(--mp-muted); }

.radio-group { display: flex; flex-wrap: wrap; gap: 12rpx; }
.radio-item {
  padding: 14rpx 24rpx; border-radius: 8rpx;
  border: 1rpx solid #C6D0DE; background: #fff;
}
.radio-item.active { border-color: var(--mp-primary); background: var(--mp-soft); }
.radio-label { font-size: 26rpx; color: var(--mp-body); }
.radio-item.active .radio-label { color: var(--mp-primary); font-weight: 600; }

.hint-card {
  background: #FFF8E8; border-radius: 10rpx; padding: 18rpx;
  border: 1rpx solid #FBF1DF;
}
.hint-text { font-size: 24rpx; color: #865C1E; display: block; line-height: 1.6; }

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
