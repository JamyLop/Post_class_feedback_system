<template>
  <view class="page">
    <view class="head">
      <text class="h1">月度评价详情</text>
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
          <text class="gen-time" v-if="report.generated_at">生成于 {{ formatTime(report.generated_at) }}</text>
        </view>
        <text v-if="report.error_message" class="error-msg">{{ report.error_message }}</text>
      </view>

      <!-- 评价内容 -->
      <view class="card">
        <view class="card-header-row">
          <text class="card-title">评价内容</text>
          <text v-if="isEditing" class="edit-hint">编辑模式</text>
        </view>
        <view v-if="isEditing" class="edit-area">
          <textarea v-model="editContent" class="textarea" :maxlength="8000" />
          <text class="char-count">{{ editContent.length }}/8000</text>
        </view>
        <view v-else class="content-area">
          <text class="content-text">{{ report.final_content || report.ai_content || '暂无内容' }}</text>
        </view>
      </view>

      <!-- 操作按钮 -->
      <view class="action-bar">
        <template v-if="report.status === 'generated' || report.status === 'published'">
          <button v-if="!isEditing" class="btn-outline" @click="startEdit">编辑</button>
          <template v-else>
            <button class="btn-outline" @click="cancelEdit">取消</button>
            <button class="btn-primary" @click="saveEdit" :loading="saving">保存</button>
          </template>
          <button v-if="report.status === 'generated'" class="btn-primary" @click="handlePublish" :loading="publishing">发布</button>
        </template>
      </view>
    </template>
  </view>
</template>

<script setup>
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
  return { generating: '生成中', generated: '已生成', published: '已发布', failed: '失败' }[s] || s
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
  editContent.value = report.value.final_content || report.value.ai_content || ''
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
    content: '发布后学生和家长可查看此评价，确认发布？',
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
.h1 { font-size: 34rpx; font-weight: 700; color: #1A1636; display: block; }
.p { font-size: 24rpx; color: #8E8B9E; display: block; margin-top: 6rpx; }

.loading-bar { text-align: center; padding: 48rpx; }
.loading-text { color: #A09CB5; font-size: 26rpx; }

.card {
  background: #fff; border-radius: 10rpx; padding: 24rpx;
  border: 1rpx solid #E0E7E5;
}
.card-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14rpx; }
.card-title { font-size: 26rpx; font-weight: 600; color: #1A1636; }
.edit-hint { font-size: 22rpx; color: #D97706; }

.status-row { display: flex; align-items: center; gap: 12rpx; }
.status-tag {
  padding: 6rpx 16rpx; border-radius: 14rpx;
  font-size: 22rpx; font-weight: 500;
}
.status-tag.is-generated { background: #E0F0E7; color: #2E7D5B; }
.status-tag.is-published { background: #EEEDFD; color: #6B5CE7; }
.status-tag.is-generating { background: #F8E8B8; color: #8A641C; }
.status-tag.is-failed { background: #F7E0D9; color: #9C4E3F; }
.status-text { white-space: nowrap; }
.gen-time { font-size: 22rpx; color: #A09CB5; }

.error-msg {
  font-size: 24rpx; color: #EF4444; background: #FEF2F2;
  border: 2rpx solid #FECACA; border-radius: 12rpx;
  padding: 16rpx; margin-top: 12rpx; display: block;
}

.content-area { min-height: 200rpx; }
.content-text { font-size: 26rpx; color: #4A4763; line-height: 1.8; white-space: pre-wrap; }

.edit-area { display: flex; flex-direction: column; gap: 8rpx; }
.textarea {
  width: 100%; min-height: 400rpx;
  border: 1rpx solid #CCD8D6; border-radius: 8rpx;
  padding: 18rpx; font-size: 26rpx; line-height: 1.8;
  background: #FAF9F7;
}
.char-count { font-size: 22rpx; color: #A09CB5; text-align: right; }

.action-bar { display: flex; gap: 16rpx; }
.btn-primary {
  flex: 1; background: #1F4F55; color: #fff; border-radius: 8rpx;
  padding: 18rpx 0; font-size: 28rpx; font-weight: 600; border: none;
}
.btn-primary::after { border: none; }
.btn-outline {
  flex: 1; background: #fff; color: #1F4F55; border: 1rpx solid #B9CCCA;
  border-radius: 8rpx; padding: 18rpx 0; font-size: 28rpx;
}
.btn-outline::after { border: none; }
</style>
