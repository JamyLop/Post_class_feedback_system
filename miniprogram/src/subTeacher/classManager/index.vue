<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">班级管理</text>
      <text class="p">管理班级与学生信息</text>
    </view>

    <view class="action-bar">
      <!-- 新建班级由德育主任操作；班主任仅维护学生名册 -->
      <button v-if="['admin', 'deyu_director'].includes(auth.role)" class="btn-primary" @click="goCreateClass">新建班级</button>
      <button v-if="['admin', 'deyu_director'].includes(auth.role)" class="btn-outline" @click="uni.navigateTo({ url: '/subTeacher/classManager/transfers' })">批量调班</button>
      <button class="btn-outline" @click="loadData" :loading="loading" :disabled="loading">刷新</button>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <EmptyState v-else-if="!classList.length" title="暂无班级" desc="点击「新建班级」开始" />
    <view v-else class="class-list">
      <view v-for="(cls, idx) in classList" :key="cls.id" class="class-card" :class="{ 'has-border': idx > 0 }">
        <view class="class-info" @click="goStudents(cls.id, cls.name)">
          <view class="class-head">
            <text class="class-name">{{ cls.name }}</text>
            <text class="class-type">{{ cls.class_type }}</text>
          </view>
          <text class="class-meta">{{ cls.education_stage }} · {{ cls.grade }} · {{ cls.school_year }}</text>
          <text v-if="cls.teacher_name" class="class-teacher">班主任：{{ cls.teacher_name }}</text>
        </view>
        <view class="class-actions">
          <button v-if="canManageClass" class="action-btn" :disabled="renaming" @click="startRename(cls)">修改名称</button>
          <text class="action-btn" @click="goStudents(cls.id, cls.name)">学生 ›</text>
        </view>
        <view v-if="editingClassId === cls.id" class="rename-form" @click.stop>
          <text class="rename-label">班级名称</text>
          <input v-model="renameName" class="rename-input" aria-label="班级名称" :maxlength="64" :disabled="renaming" :focus="true" placeholder="请输入班级名称" confirm-type="done" @confirm="saveRename(cls)" />
          <text class="rename-help">最多64个字符</text>
          <view class="rename-actions">
            <button class="btn-outline" :disabled="renaming" @click="cancelRename">取消</button>
            <button class="btn-primary" :loading="renaming" :disabled="renaming" @click="saveRename(cls)">保存名称</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listClasses, updateClass } from '../api/classes'
import EmptyState from '../../components/EmptyState.vue'
import { CLASS_MANAGEMENT_ROLES } from '../utils/constants'

const auth = useAuthStore()
const loading = ref(false)
const classList = ref([])
const canManageClass = computed(() => ['admin', 'deyu_director'].includes(auth.role))
const editingClassId = ref(null)
const renameName = ref('')
const renaming = ref(false)

function startRename(cls) {
  if (!canManageClass.value || renaming.value) return
  editingClassId.value = cls.id
  renameName.value = cls.name
}

function cancelRename() {
  if (renaming.value) return
  editingClassId.value = null
  renameName.value = ''
}

async function saveRename(cls) {
  if (!canManageClass.value || renaming.value || editingClassId.value !== cls.id) return
  const name = renameName.value.trim()
  if (!name || Array.from(name).length > 64) {
    uni.showToast({ title: '班级名称须为1至64个字符', icon: 'none' })
    return
  }
  if (name === cls.name) { cancelRename(); return }
  renaming.value = true
  try {
    // 仅提交名称，避免覆盖班主任、学年或班级分类。
    const updated = await updateClass(cls.id, { name })
    const current = classList.value.find(item => item.id === cls.id)
    if (current) current.name = updated.name
    editingClassId.value = null
    renameName.value = ''
    uni.showToast({ title: '班级名称已更新', icon: 'success' })
  } catch (_) {
    // 请求层已提示错误，保留输入便于重试。
  } finally {
    renaming.value = false
  }
}

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  // 新建班级由德育主任操作并分配班主任；班主任仅录入学生信息（可查看名册）。
  if (!CLASS_MANAGEMENT_ROLES.includes(auth.role)) {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function loadData() {
  loading.value = true
  try {
    classList.value = await listClasses()
  } catch (e) {
    classList.value = []
  } finally {
    loading.value = false
  }
}

function goCreateClass() {
  uni.navigateTo({ url: '/subTeacher/classManager/create' })
}

function goStudents(classId, className) {
  uni.navigateTo({ url: `/subTeacher/classManager/students?classId=${classId}&className=${encodeURIComponent(className)}` })
}

onShow(() => { if (guardRole()) loadData() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.action-bar { display: flex; gap: 16rpx; }
.btn-primary {
  flex: 2; background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE;
  border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.class-card {
  background: #fff; border-radius: 12rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line); display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
}
.class-card.has-border { margin-top: 16rpx; }
.class-info { flex: 1; min-width: 0; }
.class-head { display: flex; flex-wrap: wrap; align-items: center; gap: 12rpx; overflow-wrap: anywhere; }
.class-name { font-size: 30rpx; font-weight: 600; color: var(--mp-ink); }
.class-type {
  font-size: 24rpx; color: var(--mp-primary); background: var(--mp-soft);
  padding: 4rpx 10rpx; border-radius: 14rpx;
}
.class-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.class-teacher { font-size: 24rpx; color: var(--mp-body); display: block; margin-top: 4rpx; }
.class-actions { margin-left: 16rpx; display: flex; flex-direction: column; align-items: stretch; gap: 12rpx; }
.action-btn {
  font-size: 24rpx; color: var(--mp-primary); font-weight: 500;
  padding: 10rpx 16rpx; background: var(--mp-soft); border-radius: 8rpx;
  margin: 0; border: none; line-height: 1.5; text-align: center;
}
.action-btn::after { border: none; }
.rename-form { width: 100%; margin-top: 24rpx; padding-top: 24rpx; border-top: 1rpx solid var(--mp-line); }
.rename-label { display: block; font-size: 26rpx; font-weight: 600; color: var(--mp-ink); margin-bottom: 12rpx; }
.rename-input { box-sizing: border-box; width: 100%; height: 80rpx; padding: 0 20rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; font-size: 28rpx; color: var(--mp-ink); }
.rename-input:focus { border-color: var(--mp-primary); }
.rename-help { display: block; margin-top: 8rpx; font-size: 24rpx; color: var(--mp-body); }
.rename-actions { display: flex; gap: 16rpx; margin-top: 20rpx; }
.rename-actions .btn-primary, .rename-actions .btn-outline { flex: 1; margin: 0; }
</style>
