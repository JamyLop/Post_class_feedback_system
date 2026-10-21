<template>
  <el-button v-if="auth.role === 'admin'" @click="open">调整档案状态</el-button>
  <el-dialog v-model="visible" title="调整档案状态" width="min(480px, 92vw)" append-to-body :close-on-click-modal="!saving" :show-close="!saving" :close-on-press-escape="!saving">
    <p>当前状态：{{ labels[status] }}。调整会保留操作前快照并记录原因。</p>
    <el-alert v-if="['executing', 'pending_review', 'adjusted', 'archived'].includes(target)" title="此状态下家长可查看档案，请确认内容已核对。" type="warning" :closable="false" />
    <el-form label-position="top">
      <el-form-item label="目标状态"><el-select v-model="target" :disabled="saving"><el-option v-for="(label, value) in labels" :key="value" :label="label" :value="value" :disabled="value === status" /></el-select></el-form-item>
      <el-form-item label="调整原因"><el-input v-model="reason" type="textarea" :rows="3" maxlength="500" show-word-limit :disabled="saving" placeholder="填写本次调整的原因" /></el-form-item>
    </el-form>
    <template #footer><el-button :disabled="saving" @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!target || target === status || !reason.trim()" @click="save">保存状态</el-button></template>
  </el-dialog>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { changeAdminCaseStatus } from '../api/studentCases'
const props = defineProps({ caseId: Number, status: String })
const emit = defineEmits(['saved'])
const auth = useAuthStore()
const labels = { draft: '草稿', pending_confirmation: '待审查', revision_required: '待整改', executing: '执行中', pending_review: '待复盘', adjusted: '已调整', archived: '已归档' }
const visible = ref(false), saving = ref(false), target = ref(''), reason = ref('')
let expectedStatus = ''
function open() { expectedStatus = props.status; target.value = ''; reason.value = ''; visible.value = true }
async function save() {
  if (saving.value || !target.value || !reason.value.trim()) return
  saving.value = true
  try {
    await changeAdminCaseStatus(props.caseId, { target_status: target.value, expected_status: expectedStatus, reason: reason.value.trim() })
    visible.value = false; ElMessage.success('档案状态已调整'); emit('saved')
  } catch (e) { ElMessage.error(e.response?.data?.detail || '状态调整失败，请重试') }
  finally { saving.value = false }
}
</script>
