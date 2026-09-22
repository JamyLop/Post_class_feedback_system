<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">关联学生档案</text>
      <text class="p">查看您负责的学生的一生一案；可新建学生并为其建档</text>
    </view>

    <view class="action-bar">
      <button class="btn-primary" @click="goQuickStudent">新建学生</button>
      <button class="btn-outline" @click="goCreateCase">新建档案</button>
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
        <text class="empty-desc">请联系管理员将您与学生建立关联关系</text>
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
import { listStudentCases } from '../../api/studentCases'
import CaseStatusTag from '../../components/CaseStatusTag.vue'

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
.action-bar { display: flex; gap: 16rpx; }
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
