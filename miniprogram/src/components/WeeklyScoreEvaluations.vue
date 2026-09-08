<template>
  <view class="evaluations">
    <view v-for="item in score.evaluations || []" :key="item.id" class="evaluation">
      <text class="evaluation-meta">{{ item.teacher_name }} · {{ item.teacher_role === 'head_teacher' ? '班主任' : '学科老师' }} · {{ formatTime(item.updated_at) }}</text>
      <text class="evaluation-content">{{ item.content }}</text>
    </view>
    <text v-if="!score.evaluations?.length" class="empty">暂无教师评价</text>
    <button v-if="score.can_evaluate && !editing" class="edit-btn" size="mini" @click="openEditor">{{ ownEvaluation ? '修改我的评价' : '添加评价' }}</button>
    <view v-if="editing" class="editor">
      <text class="editor-label">评价内容</text>
      <textarea v-model="content" class="evaluation-input" :maxlength="2000" :disabled="saving" placeholder="填写周测表现、需改进的问题和学习建议" />
      <text class="empty">{{ content.length }}/2000</text>
      <view class="editor-actions">
        <button size="mini" :disabled="saving" @click="editing = false">取消</button>
        <button class="save-btn" size="mini" :loading="saving" :disabled="saving || !content.trim()" @click="save">保存评价</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { saveWeeklyEvaluation } from '../api/weeklyScores'

const props = defineProps({ score: { type: Object, required: true } })
const emit = defineEmits(['saved'])
const auth = useAuthStore()
const editing = ref(false)
const saving = ref(false)
const content = ref('')
const ownEvaluation = computed(() => props.score.evaluations?.find(item => item.teacher_id === auth.user?.id))
function formatTime(value) {
  if (!value) return ''
  const time = new Date(value)
  const pad = part => String(part).padStart(2, '0')
  return `${time.getFullYear()}-${pad(time.getMonth() + 1)}-${pad(time.getDate())} ${pad(time.getHours())}:${pad(time.getMinutes())}`
}
function openEditor() {
  content.value = ownEvaluation.value?.content || ''
  editing.value = true
}
async function save() {
  if (saving.value || !content.value.trim()) return
  saving.value = true
  try {
    const updated = await saveWeeklyEvaluation(props.score.id, { content: content.value.trim() })
    emit('saved', updated)
    editing.value = false
    uni.showToast({ title: '评价已保存', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: '评价保存失败，请重试', icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.evaluations { margin-top: 18rpx; border-top: 1rpx solid #DFE5ED; padding-top: 14rpx; }
.evaluation { margin-bottom: 14rpx; }
.evaluation-meta, .empty { display: block; color: #617086; font-size: 22rpx; line-height: 1.6; }
.evaluation-content { display: block; margin-top: 6rpx; color: #182337; font-size: 26rpx; line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
.edit-btn { color: #253D61; background: #EDF1F7; margin: 10rpx 0 0; }
.editor { margin-top: 14rpx; }
.editor-label { display: block; font-size: 26rpx; margin-bottom: 10rpx; }
.evaluation-input { box-sizing: border-box; width: 100%; height: 210rpx; background: #F3F5F8; border: 1rpx solid #DFE5ED; padding: 16rpx; border-radius: 8rpx; font-size: 26rpx; }
.editor-actions { display: flex; justify-content: flex-end; gap: 14rpx; margin-top: 12rpx; }
.editor-actions button { margin: 0; }
.save-btn { background: #253D61; color: #fff; }
</style>
