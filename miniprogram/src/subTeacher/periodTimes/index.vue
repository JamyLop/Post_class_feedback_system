<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">节次时间配置</text>
      <text class="p">{{ canEdit ? '配置每个节次对应的上课时间，排课时将自动显示' : '查看每个节次对应的上课时间（仅校长与德育主任可修改）' }}</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view v-if="rows.length" class="card">
        <view v-for="(row, idx) in rows" :key="row.period" class="period-row" :class="{ 'has-border': idx > 0 }">
          <view class="period-info">
            <text class="period-name">第 {{ row.period }} 节</text>
            <template v-if="editingPeriod === row.period">
              <view class="time-edit">
                <picker mode="time" :value="editForm.start_time" @change="onStartPick">
                  <view class="time-box"><text>{{ editForm.start_time || '开始' }}</text></view>
                </picker>
                <text class="time-sep">至</text>
                <picker mode="time" :value="editForm.end_time" @change="onEndPick">
                  <view class="time-box"><text>{{ editForm.end_time || '结束' }}</text></view>
                </picker>
              </view>
            </template>
            <text v-else class="period-time">{{ row.start_time }} – {{ row.end_time }} · {{ calcDuration(row.start_time, row.end_time) }}</text>
          </view>
          <view v-if="canEdit" class="period-actions">
            <template v-if="editingPeriod === row.period">
              <text class="action-link primary" @click="save(row.period)">保存</text>
              <text class="action-link" @click="cancelEdit">取消</text>
            </template>
            <text v-else class="action-link primary" @click="startEdit(row)">编辑</text>
          </view>
        </view>
      </view>
      <EmptyState v-else title="暂无节次配置" desc="请联系管理员初始化节次数据" />
      <button v-if="canEdit" class="btn-refresh" :loading="loading" @click="load">刷新</button>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import EmptyState from '../../components/EmptyState.vue'
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listPeriodTimes, updatePeriodTime } from '../api/periodTimes'

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const editingPeriod = ref(null)
const editForm = ref({ start_time: '', end_time: '' })

// 与后端 PUT 权限一致：仅校长与德育主任可写，其余角色只读
const canEdit = computed(() => ['admin', 'deyu_director'].includes(auth.role))

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (!['admin', 'deyu_director'].includes(auth.role)) {
    uni.showToast({ title: '仅校长与德育主任可访问', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

function calcDuration(start, end) {
  if (!start || !end) return '-'
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  const diff = (eh * 60 + em) - (sh * 60 + sm)
  if (!(diff > 0)) return '-'
  const hours = Math.floor(diff / 60)
  const mins = diff % 60
  return hours > 0 ? `${hours}小时${mins > 0 ? mins + '分钟' : ''}` : `${mins}分钟`
}

async function load() {
  loading.value = true
  try {
    const list = await listPeriodTimes()
    rows.value = Array.isArray(list) ? [...list].sort((a, b) => a.period - b.period) : []
  } catch (_) { rows.value = [] } finally { loading.value = false }
}

function startEdit(row) {
  editingPeriod.value = row.period
  editForm.value = { start_time: row.start_time, end_time: row.end_time }
}
function cancelEdit() { editingPeriod.value = null }
function onStartPick(e) { editForm.value.start_time = e.detail.value }
function onEndPick(e) { editForm.value.end_time = e.detail.value }

async function save(period) {
  if (!editForm.value.start_time || !editForm.value.end_time) {
    return uni.showToast({ title: '请填写开始和结束时间', icon: 'none' })
  }
  if (editForm.value.start_time >= editForm.value.end_time) {
    return uni.showToast({ title: '开始时间必须早于结束时间', icon: 'none' })
  }
  saving.value = true
  try {
    await updatePeriodTime(period, { start_time: editForm.value.start_time, end_time: editForm.value.end_time })
    uni.showToast({ title: '保存成功', icon: 'success' })
    editingPeriod.value = null
    await load()
  } catch (e) { uni.showToast({ title: e.message || '保存失败', icon: 'none' }) } finally { saving.value = false }
}

onShow(() => { if (guardRole()) load() })
</script>

<style scoped>
.page { box-sizing: border-box; width: 100%; padding: 24rpx 32rpx calc(40rpx + env(safe-area-inset-bottom)); display: flex; flex-direction: column; gap: 24rpx; }
.head { padding: 4rpx 0; }
.h1 { display: block; font-size: 38rpx; font-weight: 600; color: var(--mp-ink); }
.p { display: block; margin-top: 8rpx; font-size: 25rpx; color: var(--mp-muted); line-height: 1.6; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }
.card { background: #fff; border-radius: 16rpx; padding: 8rpx 24rpx; }
.period-row { display: flex; align-items: center; gap: 16rpx; padding: 20rpx 0; }
.period-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.period-info { flex: 1; min-width: 0; }
.period-name { display: block; font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.period-time { display: block; margin-top: 4rpx; font-size: 24rpx; color: var(--mp-muted); }
.time-edit { display: flex; align-items: center; gap: 12rpx; margin-top: 10rpx; }
.time-box { border: 2rpx solid var(--mp-line); border-radius: 12rpx; padding: 12rpx 20rpx; font-size: 26rpx; color: var(--mp-ink); background: #F7F8FA; min-width: 140rpx; text-align: center; }
.time-sep { font-size: 24rpx; color: var(--mp-muted); }
.period-actions { display: flex; gap: 16rpx; flex-shrink: 0; }
.action-link { font-size: 26rpx; color: var(--mp-muted); padding: 12rpx 0 12rpx 12rpx; }
.action-link.primary { color: var(--mp-primary); }
.btn-refresh { background: #fff; color: var(--mp-primary); border: 2rpx solid #B8C6D8; border-radius: 14rpx; padding: 20rpx 0; font-size: 26rpx; margin: 0; }
.btn-refresh::after { border: none; }
</style>
