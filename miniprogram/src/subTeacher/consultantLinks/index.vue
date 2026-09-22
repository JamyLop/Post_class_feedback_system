<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">咨询老师与学生关联</text>
      <text class="p">为咨询老师分配负责学生，与网页端「咨询老师与学生关联」同口径</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view v-if="links.length" class="card">
        <view v-for="(row, idx) in links" :key="row.id" class="link-row" :class="{ 'has-border': idx > 0 }">
          <view class="link-info">
            <text class="link-name">{{ row.consultant_name || '—' }} · {{ row.student_name || '—' }}</text>
            <text class="link-meta">{{ row.consultant_username || '' }} / {{ row.student_username || '' }}{{ row.student_channel ? ` · ${row.student_channel}` : '' }}</text>
          </view>
          <text class="danger-link" @click="remove(row)">解除</text>
        </view>
      </view>
      <EmptyState v-else title="暂无咨询老师关联记录" desc="点击下方按钮新增第一条关联" />
      <button class="btn-primary" @click="openCreate">+ 新增关联</button>
    </template>

    <view v-if="visible" class="modal-mask" @click.self="visible = false">
      <view class="modal">
        <view class="modal-header">
          <text class="modal-title">新增咨询老师关联</text>
          <text class="modal-close" @click="visible = false">✕</text>
        </view>
        <view class="form">
          <view class="field">
            <text class="label">咨询老师（班主任 / 咨询老师）</text>
            <picker :range="teachers" range-key="name" @change="onTeacherPick">
              <view class="picker"><text>{{ teacherLabel }}</text><text class="picker-arrow">›</text></view>
            </picker>
          </view>
          <view class="field">
            <text class="label">学生</text>
            <picker :range="students" range-key="name" @change="onStudentPick">
              <view class="picker"><text>{{ studentLabel }}</text><text class="picker-arrow">›</text></view>
            </picker>
          </view>
        </view>
        <view class="modal-btns">
          <button class="btn-outline" @click="visible = false">取消</button>
          <button class="btn-primary-sm" :loading="saving" :disabled="saving" @click="save">保存关联</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import EmptyState from '../../components/EmptyState.vue'
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listConsultantLinks, createConsultantLink, deleteConsultantLink, listUsers } from '../../api/studentCases'

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const links = ref([])
const teachers = ref([])
const students = ref([])
const visible = ref(false)
const form = ref({ consultant_id: null, student_id: null })

const teacherLabel = computed(() => teachers.value.find(u => u.id === form.value.consultant_id)?.name || '选择教师')
const studentLabel = computed(() => students.value.find(u => u.id === form.value.student_id)?.name || '选择学生')
function onTeacherPick(e) { form.value.consultant_id = teachers.value[e.detail.value]?.id ?? null }
function onStudentPick(e) { form.value.student_id = students.value[e.detail.value]?.id ?? null }

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'admin') {
    uni.showToast({ title: '仅校长可访问', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function load() {
  loading.value = true
  try { links.value = await listConsultantLinks() } catch (_) { links.value = [] } finally { loading.value = false }
}

async function openCreate() {
  form.value = { consultant_id: null, student_id: null }
  try {
    // 与网页端一致：班主任与咨询老师均可被选为负责教师
    const [ts, cs, ss] = await Promise.all([
      listUsers({ role: 'teacher' }).catch(() => []),
      listUsers({ role: 'consultant' }).catch(() => []),
      listUsers({ role: 'student' }),
    ])
    teachers.value = [...(Array.isArray(ts) ? ts : []), ...(Array.isArray(cs) ? cs : [])]
    students.value = Array.isArray(ss) ? ss : []
  } catch (_) { teachers.value = []; students.value = [] }
  visible.value = true
}

async function save() {
  if (!form.value.consultant_id || !form.value.student_id) {
    return uni.showToast({ title: '请选择咨询老师和学生', icon: 'none' })
  }
  saving.value = true
  try {
    await createConsultantLink({ ...form.value })
    uni.showToast({ title: '咨询老师关联已建立', icon: 'success' })
    visible.value = false
    load()
  } catch (e) { uni.showToast({ title: e.message || '保存失败', icon: 'none' }) } finally { saving.value = false }
}

function remove(row) {
  uni.showModal({
    title: '解除关联',
    content: `确认解除「${row.consultant_name}」与「${row.student_name}」的关联？`,
    success: async (res) => {
      if (!res.confirm) return
      try {
        await deleteConsultantLink(row.id)
        uni.showToast({ title: '关联已解除', icon: 'success' })
        load()
      } catch (_) {}
    },
  })
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
.link-row { display: flex; align-items: center; gap: 16rpx; padding: 20rpx 0; }
.link-row.has-border { border-top: 2rpx solid var(--mp-soft); }
.link-info { flex: 1; min-width: 0; }
.link-name { display: block; font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.link-meta { display: block; margin-top: 4rpx; font-size: 24rpx; color: var(--mp-muted); }
.danger-link { font-size: 26rpx; color: #A33E39; flex-shrink: 0; padding: 12rpx 0 12rpx 12rpx; }
.btn-primary { background: var(--mp-primary); color: #fff; border-radius: 14rpx; padding: 22rpx 0; font-size: 28rpx; font-weight: 600; border: none; margin: 0; }
.btn-primary::after { border: none; }
.btn-primary-sm { background: var(--mp-primary); color: #fff; border-radius: 14rpx; padding: 20rpx 32rpx; font-size: 28rpx; font-weight: 600; border: none; margin: 0; flex: 1; }
.btn-primary-sm::after { border: none; }
.btn-outline { background: #fff; color: var(--mp-primary); border: 2rpx solid #B8C6D8; border-radius: 14rpx; padding: 20rpx 0; font-size: 28rpx; flex: 1; }
.btn-outline::after { border: none; }
.modal-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(26,22,54,0.45); display: flex; align-items: flex-end; z-index: 999; }
.modal { background: #fff; border-radius: 24rpx 24rpx 0 0; padding: 28rpx; width: 100%; max-height: 80vh; overflow-y: auto; display: flex; flex-direction: column; gap: 16rpx; }
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 32rpx; font-weight: 700; color: var(--mp-ink); }
.modal-close { font-size: 28rpx; color: var(--mp-muted); padding: 8rpx; }
.form { display: flex; flex-direction: column; gap: 14rpx; }
.field { display: flex; flex-direction: column; gap: 8rpx; }
.label { font-size: 24rpx; font-weight: 600; color: var(--mp-ink); }
.picker { border: 2rpx solid var(--mp-line); border-radius: 14rpx; padding: 18rpx 20rpx; background: #fff; font-size: 26rpx; color: var(--mp-ink); display: flex; justify-content: space-between; align-items: center; }
.picker-arrow { color: var(--mp-muted); }
.modal-btns { display: flex; gap: 14rpx; margin-top: 8rpx; }
</style>
