<template>
  <view v-if="auth.role === 'admin'" class="status-maintenance">
    <button size="mini" @click="open">调整档案状态</button>
    <view v-if="visible" class="status-form">
      <text>当前：{{ labels[status] }}。调整会保留操作前快照并记录原因。</text>
      <picker :range="options" range-key="label" :disabled="saving" @change="target = options[Number($event.detail.value)].value"><view class="control">目标状态：{{ labels[target] || '请选择' }}</view></picker>
      <text v-if="['executing', 'pending_review', 'adjusted', 'archived'].includes(target)">此状态下家长可查看档案，请确认内容已核对。</text>
      <textarea v-model="reason" :maxlength="500" :disabled="saving" placeholder="调整原因（必填）" class="control" />
      <view class="buttons"><button size="mini" :disabled="saving" @click="visible = false">取消</button><button size="mini" :loading="saving" :disabled="saving || !target || !reason.trim()" @click="save">保存状态</button></view>
    </view>
  </view>
</template>
<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { changeAdminCaseStatus } from '../api/studentCases'
const props = defineProps({ caseId: Number, status: String })
const emit = defineEmits(['saved'])
const auth = useAuthStore()
const labels = { draft: '草稿', pending_confirmation: '待审查', revision_required: '待整改', executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }
const options = computed(() => Object.entries(labels).filter(([value]) => value !== props.status).map(([value, label]) => ({ value, label })))
const visible = ref(false), saving = ref(false), target = ref(''), reason = ref('')
let expectedStatus = ''
function open() { expectedStatus = props.status; target.value = ''; reason.value = ''; visible.value = true }
async function save() {
  if (saving.value || !target.value || !reason.value.trim()) return
  saving.value = true
  try {
    await changeAdminCaseStatus(props.caseId, { target_status: target.value, expected_status: expectedStatus, reason: reason.value.trim() })
    visible.value = false; uni.showToast({ title: '状态已调整' }); emit('saved')
  } catch (e) { uni.showToast({ title: e.message || '状态调整失败', icon: 'none' }) }
  finally { saving.value = false }
}
</script>
<style scoped>
.status-maintenance { margin-top: 20rpx; }.status-maintenance button { margin: 0; color: var(--mp-primary); }.status-form { display: flex; flex-direction: column; gap: 20rpx; padding-top: 20rpx; font-size: 26rpx; color: var(--mp-ink); }.control { width: 100%; box-sizing: border-box; padding: 18rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; }.buttons { display: flex; gap: 20rpx; }
</style>
