<template>
  <view class="page">
    <view class="head">
      <text class="h1">新建学生</text>
      <text class="p">在 {{ className }} 中添加学生</text>
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
              @click="form.gender = g"
            >
              <text class="radio-label">{{ g }}</text>
            </view>
          </view>
        </view>
        <view class="field">
          <text class="field-label">民族</text>
          <input v-model="form.ethnicity" placeholder="如：汉族" class="input" />
        </view>
        <view class="field">
          <text class="field-label">生源学校</text>
          <input v-model="form.source_school" placeholder="如：XX中学" class="input" />
        </view>
      </view>
    </view>

    <view class="card">
      <text class="card-title">家长信息</text>
      <view class="form">
        <view class="field">
          <text class="field-label">家长姓名</text>
          <input v-model="form.parent_name" placeholder="请输入家长姓名" class="input" />
        </view>
        <view class="field">
          <text class="field-label">家长手机号 <text class="required">*</text></text>
          <input v-model="form.parent_phone" type="number" placeholder="11位手机号（必填）" class="input" />
        </view>
        <view class="field">
          <text class="field-label">与学生关系</text>
          <view class="radio-group">
            <view
              v-for="r in relationshipOptions"
              :key="r"
              class="radio-item"
              :class="{ active: form.parent_relationship === r }"
              @click="form.parent_relationship = r"
            >
              <text class="radio-label">{{ r }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view class="hint-card">
      <text class="hint-text">* 学生账号将自动生成，初始密码为 123456</text>
      <text class="hint-text">* 家长手机号将自动注册为家长账号，初始密码 88888888</text>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :loading="submitting" @click="handleSubmit">
        {{ submitting ? '创建中...' : '创建并入班' }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { createAndEnrollStudent } from '../../api/classes'

const classId = ref(null)
const className = ref('')
const submitting = ref(false)

const genderOptions = ['男', '女']
const relationshipOptions = ['父亲', '母亲', '其他']

const form = reactive({
  name: '',
  gender: '',
  ethnicity: '',
  source_school: '',
  parent_name: '',
  parent_phone: '',
  parent_relationship: '父亲',
})

onLoad((options) => {
  classId.value = Number(options.classId)
  className.value = decodeURIComponent(options.className || '')
})

function validate() {
  if (!form.name.trim()) {
    uni.showToast({ title: '请输入学生姓名', icon: 'none' })
    return false
  }
  if (!form.parent_phone.trim()) {
    uni.showToast({ title: '请输入家长手机号', icon: 'none' })
    return false
  }
  if (!/^1[3-9]\d{9}$/.test(form.parent_phone.trim())) {
    uni.showToast({ title: '手机号格式不正确', icon: 'none' })
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
      gender: form.gender,
      ethnicity: form.ethnicity.trim(),
      source_school: form.source_school.trim(),
      parent_name: form.parent_name.trim(),
      parent_phone: form.parent_phone.trim(),
      parent_relationship: form.parent_relationship,
    })
    uni.showToast({ title: '创建成功', icon: 'success' })
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
.input {
  border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 18rpx 22rpx; font-size: 28rpx; background: #fff;
}

.radio-group { display: flex; flex-wrap: wrap; gap: 12rpx; }
.radio-item {
  padding: 14rpx 24rpx; border-radius: 8rpx;
  border: 1rpx solid #CCD8D6; background: #fff;
}
.radio-item.active { border-color: #1F4F55; background: #DDEBE8; }
.radio-label { font-size: 26rpx; color: #4A4763; }
.radio-item.active .radio-label { color: #1F4F55; font-weight: 600; }

.hint-card {
  background: #FFF8E8; border-radius: 10rpx; padding: 18rpx;
  border: 1rpx solid #F8E8B8;
}
.hint-text { font-size: 22rpx; color: #8A641C; display: block; line-height: 1.6; }

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
