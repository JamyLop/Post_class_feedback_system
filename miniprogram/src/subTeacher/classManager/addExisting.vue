<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">选择已有学生</text>
      <text class="p">在 {{ className }} 中加入已建账号的学生</text>
    </view>

    <view class="hint-card">
      <text class="hint-text">可搜索咨询老师新建的未分班学生，选中后加入本班级</text>
    </view>

    <view class="card">
      <input v-model="keyword" placeholder="搜索学生用户名 / 姓名" class="input" @input="onSearch" />
      <view class="enroll-row">
        <text class="enroll-label">入学月份</text>
        <picker :range="monthOptions" :value="monthIndex" @change="onMonthChange">
          <view class="input picker-input">
            <text>{{ enrollMonth }} 月</text>
            <text class="picker-arrow">⌄</text>
          </view>
        </picker>
      </view>
      <text class="enroll-hint">咨询建的临时账号（ZX开头）入班时按此月份重编正式学号，位号自动取空位</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <EmptyState v-else-if="!candidates.length" title="暂无匹配学生" desc="输入关键词搜索学生" />
    <view v-else class="candidate-list">
      <view
        v-for="stu in candidates"
        :key="stu.id"
        class="candidate-card"
        :class="{ selected: selectedIds.has(stu.id) }"
        @click="toggle(stu.id)"
      >
        <view class="check" :class="{ on: selectedIds.has(stu.id) }">
          <text v-if="selectedIds.has(stu.id)" class="check-mark">✓</text>
        </view>
        <view class="candidate-info">
          <text class="candidate-name">{{ stu.name }}</text>
          <text class="candidate-meta">{{ stu.username }}{{ (stu.username || '').startsWith('ZX') ? ' · 临时账号，入班重编' : '' }}</text>
        </view>
      </view>
    </view>

    <view class="submit-bar">
      <button class="btn-submit" :disabled="!selectedIds.size || submitting" :loading="submitting" @click="handleSubmit">
        {{ submitting ? '添加中...' : `添加选中学生 (${selectedIds.size})` }}
      </button>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { addStudentsToClass, listUsers } from '../api/classes'
import EmptyState from '../../components/EmptyState.vue'

const classId = ref(null)
const className = ref('')
const keyword = ref('')
const loading = ref(false)
const submitting = ref(false)
const candidates = ref([])
const selectedIds = ref(new Set())
const enrollMonth = ref(7)
const monthOptions = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
const monthIndex = computed(() => (enrollMonth.value || 7) - 1)

function onMonthChange(e) {
  enrollMonth.value = Number(e.detail.value) + 1
}

onLoad((options) => {
  classId.value = Number(options.classId)
  className.value = decodeURIComponent(options.className || '')
})

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadCandidates, 400)
}

async function loadCandidates() {
  loading.value = true
  try {
    const list = await listUsers('student', keyword.value.trim())
    candidates.value = Array.isArray(list) ? list : []
  } catch (_) {
    candidates.value = []
  } finally {
    loading.value = false
  }
}

function toggle(id) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

async function handleSubmit() {
  if (!selectedIds.value.size) {
    uni.showToast({ title: '请先选择学生', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    const ids = [...selectedIds.value]
    const tmpIds = new Set(
      candidates.value.filter((s) => `${s.username || ''}`.startsWith('ZX') && selectedIds.value.has(s.id)).map((s) => s.id),
    )
    const added = await addStudentsToClass(classId.value, ids, enrollMonth.value ? { enrollment_month: enrollMonth.value } : {})
    const renamed = (added || []).filter((s) => tmpIds.has(s.id) && !`${s.username || ''}`.startsWith('ZX'))
    uni.showToast({ title: renamed.length ? `添加成功，${renamed.length}个临时账号已重编` : '添加成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 1200)
  } catch (_) {
    // 错误已统一提示
  } finally {
    submitting.value = false
  }
}

onMounted(loadCandidates)
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; padding-bottom: 140rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.hint-card { background: #FFF8E8; border-radius: 10rpx; padding: 18rpx; border: 1rpx solid #FBF1DF; }
.hint-text { font-size: 24rpx; color: #865C1E; display: block; line-height: 1.6; }
.card { background: #fff; border-radius: 10rpx; padding: 24rpx; border: 1rpx solid var(--mp-line); display: flex; flex-direction: column; gap: 16rpx; }
.input { border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 22rpx; font-size: 28rpx; background: #fff; }
.picker-input { display: flex; align-items: center; justify-content: space-between; }
.picker-arrow { color: var(--mp-muted); }
.enroll-row { display: flex; align-items: center; gap: 16rpx; }
.enroll-label { font-size: 26rpx; color: var(--mp-body); white-space: nowrap; }
.enroll-hint { font-size: 24rpx; color: var(--mp-muted); line-height: 1.6; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.candidate-list { display: flex; flex-direction: column; gap: 12rpx; }
.candidate-card { background: #fff; border-radius: 12rpx; padding: 20rpx; border: 1rpx solid var(--mp-line); display: flex; align-items: center; gap: 16rpx; }
.candidate-card.selected { border-color: var(--mp-primary); background: var(--mp-soft); }
.check { width: 44rpx; height: 44rpx; border-radius: 50%; border: 2rpx solid #C6D0DE; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.check.on { background: var(--mp-primary); border-color: var(--mp-primary); }
.check-mark { color: #fff; font-size: 28rpx; font-weight: 700; }
.candidate-info { flex: 1; }
.candidate-name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.candidate-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.submit-bar { position: fixed; left: 0; right: 0; bottom: 0; background: #fff; padding: 20rpx 28rpx; padding-bottom: calc(20rpx + env(safe-area-inset-bottom)); border-top: 1rpx solid var(--mp-line); }
.btn-submit { background: var(--mp-primary); color: #fff; border-radius: 8rpx; padding: 24rpx 0; font-size: 30rpx; font-weight: 600; border: none; }
.btn-submit::after { border: none; }
</style>
