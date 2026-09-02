<template>
  <view class="page">
    <view class="filters">
      <picker :range="classOptions" range-key="name" @change="onClassChange">
        <view class="picker">{{ selectedClassName || '全部班级' }}</view>
      </picker>
      <picker :range="statusOptions" range-key="label" @change="onStatusChange">
        <view class="picker">{{ selectedStatusLabel || '全部状态' }}</view>
      </picker>
    </view>

    <view v-if="loading" class="tip">加载中…</view>
    <template v-else>
      <text class="count">共 {{ rows.length }} 条档案</text>
      <view v-if="rows.length" class="list">
        <view v-for="c in rows" :key="c.id" class="row" @click="openDetail(c.id)">
          <view class="row-top">
            <text class="name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
            <CaseStatusTag :status="c.status" />
          </view>
          <text class="meta">{{ c.class_name }} · 第{{ c.version }}版 · {{ (c.updated_at||'').slice(0,10) }}</text>
        </view>
      </view>
      <EmptyState v-else title="暂无档案" desc="请在 Web 端新建学生档案" />
    </template>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases, listClasses } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const auth = useAuthStore()
const loading = ref(false)
const rows = ref([])
const classes = ref([])
const selectedClassId = ref(null)
const selectedStatus = ref(null)

const classOptions = computed(() => [{ id: null, name: '全部班级' }, ...classes.value])
const statusOptions = [
  { value: null, label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'pending_confirmation', label: '待德育审查' },
  { value: 'revision_required', label: '待整改' },
  { value: 'executing', label: '执行中' },
  { value: 'pending_review', label: '待复盘' },
  { value: 'adjusted', label: '已调整' },
  { value: 'archived', label: '已归档' },
]
const selectedClassName = computed(() => classOptions.value.find(c => c.id === selectedClassId.value)?.name || '')
const selectedStatusLabel = computed(() => statusOptions.find(s => s.value === selectedStatus.value)?.label || '')

function onClassChange(e) {
  selectedClassId.value = classOptions.value[e.detail.value]?.id || null
  load()
}
function onStatusChange(e) {
  selectedStatus.value = statusOptions[e.detail.value]?.value || null
  load()
}

function guardRole() {
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' }); return false
  }
  if (!['teacher', 'deyu_director', 'admin'].includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (selectedClassId.value) params.class_id = selectedClassId.value
    if (selectedStatus.value) params.status = selectedStatus.value
    rows.value = await listStudentCases(params)
  } catch (_) { rows.value = [] } finally { loading.value = false }
}

function openDetail(id) { uni.navigateTo({ url: `/subTeacher/caseDetail/index?id=${id}` }) }

onShow(() => {
  if (guardRole()) {
    listClasses().then(c => { classes.value = Array.isArray(c) ? c : [] }).catch(() => {})
    load()
  }
})
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:16rpx; }
.filters { display:flex; gap:12rpx; }
.picker { flex:1; border:1rpx solid #e2e8f0; border-radius:10rpx; padding:16rpx 18rpx; background:#fff; font-size:26rpx; color:#334155; }
.count { font-size:22rpx; color:#94a3b8; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
.list { display:flex; flex-direction:column; gap:12rpx; }
.row { background:#fff; border:1rpx solid #e2e8f0; border-radius:12rpx; padding:20rpx; }
.row-top { display:flex; justify-content:space-between; align-items:center; }
.name { font-size:28rpx; font-weight:600; color:#0f172a; }
.meta { font-size:22rpx; color:#94a3b8; display:block; margin-top:6rpx; }
</style>
