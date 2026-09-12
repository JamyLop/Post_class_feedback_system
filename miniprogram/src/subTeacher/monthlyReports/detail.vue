<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head">
      <text class="h1">月度评定详情</text>
      <text class="p">{{ report?.student_name || '' }} · {{ report?.month_label || '' }}</text>
    </view>

    <view v-if="loading" class="loading-bar">
      <text class="loading-text">加载中...</text>
    </view>
    <template v-else-if="report">
      <!-- 状态信息 -->
      <view class="card">
        <view class="status-row">
          <view class="status-tag" :class="`is-${report.status}`">
            <text class="status-text">{{ statusLabel(report.status) }}</text>
          </view>
          <text class="gen-time" v-if="report.updated_at">更新于 {{ formatTime(report.updated_at) }}</text>
        </view>
        <text v-if="report.error_message" class="error-msg">{{ report.error_message }}</text>
      </view>

      <!-- 评定内容 -->
      <view class="card">
        <view class="card-header-row">
          <text class="card-title">评定内容</text>
          <text v-if="isEditing" class="edit-hint">编辑模式</text>
        </view>
        <view v-if="isEditing" class="edit-area">
          <textarea v-model="editContent" class="textarea" :maxlength="8000" />
          <text class="char-count">{{ editContent.length }}/8000</text>
        </view>
        <view v-else class="content-area">
          <text class="content-text">{{ report.final_content || '请点击编辑填写评定内容' }}</text>
        </view>
      </view>

      <!-- 操作按钮 -->
      <view class="action-bar">
        <template v-if="['generated', 'published', 'generating', 'failed'].includes(report.status)">
          <button v-if="!isEditing" class="btn-outline" @click="startEdit">编辑</button>
          <template v-else>
            <button class="btn-outline" @click="cancelEdit">取消</button>
            <button class="btn-primary" @click="saveEdit" :loading="saving" :disabled="saving">保存</button>
          </template>
          <button v-if="report.status === 'generated' && !isEditing" class="btn-primary" @click="handlePublish" :loading="publishing" :disabled="publishing">发布</button>
        </template>
      </view>
    </template>
  </view>
</template>

<script setup>
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { ref, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getMonthlyReport, updateMonthlyReport, publishMonthlyReport } from '../../api/monthlyReports'

const report = ref(null)
const loading = ref(false)
const isEditing = ref(false)
const editContent = ref('')
const saving = ref(false)
const publishing = ref(false)

function statusLabel(s) {
  return { generating: '待填写', generated: '待发布', published: '已发布', failed: '待补充' }[s] || s
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onLoad((options) => {
  loadReport(Number(options.id))
})

async function loadReport(id) {
  loading.value = true
  try {
    report.value = await getMonthlyReport(id)
  } catch (e) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function startEdit() {
  editContent.value = report.value.final_content || ''
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  editContent.value = ''
}

async function saveEdit() {
  if (!editContent.value.trim()) {
    uni.showToast({ title: '内容不能为空', icon: 'none' })
    return
  }
  saving.value = true
  try {
    report.value = await updateMonthlyReport(report.value.id, { final_content: editContent.value.trim() })
    isEditing.value = false
    uni.showToast({ title: '保存成功', icon: 'success' })
  } catch (e) {
    // 错误已处理
  } finally {
    saving.value = false
  }
}

async function handlePublish() {
  uni.showModal({
    title: '确认发布',
    content: '发布后学生和家长可查看此评定，确认发布？',
    success: async (res) => {
      if (!res.confirm) return
      publishing.value = true
      try {
        report.value = await publishMonthlyReport(report.value.id)
        uni.showToast({ title: '发布成功', icon: 'success' })
      } catch (e) {
        // 错误已处理
      } finally {
        publishing.value = false
      }
    }
  })
}
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; }
.h1 { font-size: 34rpx; font-weight: 700; color: var(--mp-ink); display: block; }
.p { font-size: 24rpx; color: var(--mp-muted); display: block; margin-top: 6rpx; }

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: var(--mp-muted); font-size: 26rpx; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid var(--mp-line);
}
.card-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14rpx; }
.card-title { font-size: 26rpx; font-weight: 600; color: var(--mp-ink); }
.edit-hint { font-size: 24rpx; color: #865C1E; }

.status-row { display: flex; align-items: center; gap: 12rpx; }
.status-tag {
  padding: 6rpx 16rpx; border-radius: 14rpx;
  font-size: 24rpx; font-weight: 500;
}
.status-tag.is-generated { background: #EAF3EE; color: #286349; }
.status-tag.is-published { background: var(--mp-soft); color: var(--mp-primary); }
.status-tag.is-generating { background: #FBF1DF; color: #865C1E; }
.status-tag.is-failed { background: #FAECE9; color: #A33E39; }
.status-text { white-space: nowrap; }
.gen-time { font-size: 24rpx; color: var(--mp-muted); }

.error-msg {
  font-size: 24rpx; color: #A33E39; background: #FEF2F2;
  border: 2rpx solid #FECACA; border-radius: 12rpx;
  padding: 16rpx; margin-top: 12rpx; display: block;
}

.content-area { min-height: 200rpx; }
.content-text { font-size: 26rpx; color: var(--mp-body); line-height: 1.8; white-space: pre-wrap; }

.edit-area { display: flex; flex-direction: column; gap: 8rpx; }
.textarea {
  width: 100%; min-height: 400rpx;
  border: 1rpx solid #C6D0DE; border-radius: 8rpx;
  padding: 18rpx; font-size: 26rpx; line-height: 1.8;
  background: #F7F8FA;
}
.char-count { font-size: 24rpx; color: var(--mp-muted); text-align: right; }

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
</style>
