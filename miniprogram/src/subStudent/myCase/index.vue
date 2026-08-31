<template>
  <view class="page">
    <view class="head">
      <text class="h1">我的档案</text>
      <text class="p">只读查看已发布的一生一案（需后端开放学生自查权限后可见）</text>
    </view>
    <view v-if="loading" class="tip">加载中…</view>
    <template v-else-if="detail">
      <view class="card">
        <text class="name">{{ detail.student_name }}</text>
        <CaseStatusTag :status="detail.status" />
        <text class="body">{{ detail.overall_problem?.slice(0,120) || '—' }}</text>
      </view>
    </template>
    <EmptyState v-else title="暂无可查看档案" desc="班主任尚未发布可查看版本，或学生自查权限尚未开放（P1）" />
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { http } from '../../utils/request'
import CaseStatusTag from '../../components/CaseStatusTag.vue'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(false)
const detail = ref(null)

async function load() {
  loading.value = true
  try {
    // 约定后端为学生提供 /student-cases/my-case 或复用详情权限；此处尝试拉取，需后端 P1 完成
    detail.value = await http.get('/student-cases/my-case').catch(async () => {
      // 降级：尝试通过学生 id 查可见列表的第一条
      const me = await http.get('/auth/me')
      const list = await http.get('/student-cases', { student_id: me.id }).catch(()=>[])
      return Array.isArray(list) && list.length ? await http.get(`/student-cases/${list[0].id}`) : null
    })
  } catch (_) { detail.value = null } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.page { padding:28rpx; display:flex; flex-direction:column; gap:20rpx; }
.h1 { font-size:32rpx; font-weight:700; color:#0f172a; }
.p { font-size:24rpx; color:#64748b; margin-top:6rpx; display:block; }
.tip { text-align:center; color:#64748b; padding:32rpx; }
.card { background:#fff; border:1rpx solid #e2e8f0; border-radius:16rpx; padding:24rpx; }
.name { font-size:28rpx; font-weight:600; color:#0f172a; display:block; }
.body { font-size:24rpx; color:#475569; display:block; margin-top:12rpx; line-height:1.6; }
</style>
