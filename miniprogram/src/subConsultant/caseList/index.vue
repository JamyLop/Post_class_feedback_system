<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">关联学生档案</text>
      <text class="p">查看您负责的学生的一生一案；可关联已有学生或新建学生后撰写</text>
    </view>

    <view class="action-bar">
      <button class="btn-outline" @click="openLinkStudent">关联已有学生</button>
      <button class="btn-primary" @click="goQuickStudent">新建学生</button>
      <button class="btn-outline" @click="goCreateCase">新建档案</button>
    </view>
    <view v-if="linkVisible" class="empty-card link-panel">
      <text class="empty-title">关联已有学生</text>
      <input v-model="linkKeyword" placeholder="学生姓名或学号" class="input" @confirm="searchLinkStudents" />
      <button class="btn-outline" :disabled="linkLoading" @click="searchLinkStudents">搜索</button>
      <text v-if="linkLoading">加载中...</text>
      <text v-else-if="!linkOptions.length">未找到学生</text>
      <view v-for="student in linkOptions" :key="student.id" class="link-row">
        <text>{{ student.name }} · {{ student.username }}</text>
        <button class="btn-outline" :disabled="student.linked || linking" @click="submitLinkStudent(student)">{{ student.linked ? '已关联' : '关联并撰写' }}</button>
      </view>
      <view class="action-bar">
        <button class="btn-outline" :disabled="!linkOffset || linkLoading" @click="loadLinkStudents(linkOffset - 50)">上一页</button>
        <button class="btn-outline" :disabled="linkOptions.length < 50 || linkLoading" @click="loadLinkStudents(linkOffset + 50)">下一页</button>
        <button class="btn-outline" @click="linkVisible = false">关闭</button>
      </view>
    </view>
    <view class="search-bar">
      <input v-model="keyword" placeholder="搜索学生姓名" class="input" @input="onSearch" />
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else>
      <view v-if="!cases.length" class="empty-card">

        <text class="empty-title">暂无关联学生</text>
        <text class="empty-desc">可选择已有学生关联后建档撰写</text>
      </view>

      <view v-else class="case-list">
        <view v-for="c in filteredCases" :key="c.id" class="case-card" @click="openCase(c.id)">
          <view class="case-top">
            <view class="case-info">
              <text class="case-name">{{ c.student_name || `学生 #${c.student_id}` }}</text>
              <text class="case-meta">{{ c.class_name || '未分班' }} · 第{{ c.version }}版</text>
            </view>
            <CaseStatusTag :status="c.status" />
          </view>
          <text class="case-time">更新于 {{ (c.updated_at || '').slice(0, 10) }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listStudentCases, listConsultantStudents, linkConsultantStudent } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'

const linkVisible = ref(false)
const linkKeyword = ref('')
const linkOptions = ref([])
const linkOffset = ref(0)
const linkLoading = ref(false)
const linking = ref(false)
async function loadLinkStudents(offset = 0) {
  linkLoading.value = true
  try {
    linkOptions.value = await listConsultantStudents({ keyword: linkKeyword.value.trim(), offset, limit: 50 })
    linkOffset.value = offset
  } catch (_) {} finally { linkLoading.value = false }
}
function searchLinkStudents() { return loadLinkStudents(0) }
function openLinkStudent() {
  linkVisible.value = true
  linkKeyword.value = ''
  linkOptions.value = []
  loadLinkStudents()
}
async function submitLinkStudent(student) {
  if (linking.value) return
  linking.value = true
  try {
    await linkConsultantStudent(student.id)
    uni.showToast({ title: '关联成功', icon: 'success' })
    linkVisible.value = false
    await refresh()
    const existing = cases.value.find(c => c.student_id === student.id)
    if (existing) openCase(existing.id)
    else uni.navigateTo({ url: `/subConsultant/createCase/index?studentId=${student.id}` })
  } catch (_) {} finally { linking.value = false }
}

const auth = useAuthStore()
const loading = ref(false)
const cases = ref([])
const keyword = ref('')
const filteredCases = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return cases.value
  return cases.value.filter((c) => `${c.student_name || ''}${c.class_name || ''}`.toLowerCase().includes(q))
})

function guardRole() {
  if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }
  if (auth.role !== 'consultant') {
    uni.showToast({ title: '当前角色无权限', icon: 'none' }); uni.reLaunch({ url: '/pages/index/index' }); return false
  }
  return true
}

async function refresh() {
  loading.value = true
  try {
    const list = await listStudentCases().catch(() => [])
    cases.value = Array.isArray(list) ? list : []
  } finally { loading.value = false }
}

function openCase(id) {
  uni.navigateTo({ url: `/subConsultant/caseDetail/index?id=${id}` })
}

function goQuickStudent() {
  uni.navigateTo({ url: '/subConsultant/quickStudent/index' })
}

function goCreateCase() {
  uni.navigateTo({ url: '/subConsultant/createCase/index' })
}

function onSearch() {}

onShow(() => { if (guardRole()) refresh() })
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }
.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.empty-card {
  background: #fff; border-radius: 16rpx; padding: 64rpx 28rpx;
  display: flex; flex-direction: column; align-items: center; gap: 12rpx;
  border: 1rpx solid var(--mp-line);
}
.empty-icon { font-size: 48rpx; }
.empty-title { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); }
.empty-desc { font-size: 24rpx; color: var(--mp-muted); }

.case-list { display: flex; flex-direction: column; gap: 14rpx; }
.case-card {
  background: #fff; border-radius: 14rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.case-top { display: flex; justify-content: space-between; align-items: center; }
.case-info { flex: 1; }
.case-name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); display: block; }
.case-meta { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 4rpx; }
.case-time { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 10rpx; }
.action-bar { display: flex; flex-wrap: wrap; gap: 16rpx; }
.link-panel { padding: 24rpx; align-items: stretch; }
.link-row { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; font-size: 26rpx; }
.link-row .btn-outline { flex: none; padding: 12rpx; margin: 0; }
.btn-primary {
  flex: 1; background: var(--mp-primary); color: #fff; border-radius: 8rpx;
  padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; background: #fff; color: var(--mp-primary); border: 1rpx solid #C6D0DE;
  border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }
.search-bar { margin-top: 4rpx; }
.input { border: 1rpx solid #C6D0DE; border-radius: 8rpx; padding: 18rpx 22rpx; font-size: 28rpx; background: #fff; }
</style>
