<template>
  <view class="page">
    <WorkspaceLink />
    <text class="h1">批量调班</text>
    <text class="help">仅德育主任和管理员可操作。保留学号和历史记录，交接当前档案与待办。</text>
    <view class="tabs"><button :class="{ active: tab === 'edit' }" @click="tab = 'edit'">调整名单</button><button :class="{ active: tab === 'history' }" @click="showHistory">调班记录</button></view>
    <template v-if="tab === 'edit'">
      <view class="panel">
        <text class="h2">选择原班级与学生</text>
        <picker :range="classes" range-key="label" @change="selectSource"><view class="field">{{ source?.name || '选择原班级' }} ›</view></picker>
        <text v-if="!source" class="help block">先选择原班级，再勾选一个或多个学生。</text>
        <text v-else class="help block">学生名单共 {{ roster.length }} 人，已选 {{ selected.length }} 人，可单选或多选。</text>
        <text v-if="rosterLoading" class="help">正在加载学生…</text>
        <checkbox-group @change="selected = $event.detail.value">
          <label v-for="student in roster" :key="student.id" class="student-row"><checkbox :value="student.username" :checked="selected.includes(student.username)" /><view><text>{{ student.name }}</text><text class="help block">{{ student.username }}</text></view></label>
        </checkbox-group>
        <template v-if="source">
          <text v-if="!rosterLoading && !roster.length" class="help block">该班暂无学生。</text>
          <text class="field-label">将所选 {{ selected.length }} 名学生调至</text>
          <picker :range="targets" range-key="label" :disabled="!selected.length || busy" @change="target = targets[Number($event.detail.value)]"><view class="field">{{ target?.name || '勾选学生后选择目标班级' }} ›</view></picker>
          <button class="secondary" :disabled="!selected.length || !target || busy" @click="addSelected">加入调班名单（{{ selected.length }}）</button>
        </template>
      </view>
      <view class="panel">
        <text class="h2">待调整名单 · {{ rows.length }} 人</text>
        <text v-if="!rows.length" class="help">选择原班级，勾选学生并指定目标班级后，先预览再确认生效。</text>
        <view v-for="(row, index) in rows" :key="row.student_username" class="transfer-row">
          <view class="row-head"><text>{{ preview?.rows[index]?.student_name || row.student_name || row.student_username }}</text><text class="remove" @click="removeRow(index)">移除</text></view>
          <text class="help block">{{ row.student_username }}</text>
          <text class="block">{{ preview?.rows[index]?.source_class_name || sourceName(row) }} → {{ targetName(row) }}</text>
          <template v-if="preview?.rows[index]">
            <text v-for="error in preview.rows[index].errors" :key="error" class="error block">{{ error }}</text>
            <text v-if="!preview.rows[index].errors.length" class="help block">可交接 · {{ preview.rows[index].case_count }} 份当前档案</text>
            <view v-for="assignment in preview.rows[index].assignments" :key="assignment.subject">
              <picker v-if="assignment.options.length > 1" :range="assignment.options" range-key="name" @change="chooseTeacher(index, assignment, $event)"><view class="field">{{ assignment.subject }}接手老师：{{ teacherName(row, assignment) }} ›</view></picker>
            </view>
          </template>
        </view>
        <view v-if="preview" class="summary">
          <text class="block">{{ !fresh ? '名单已修改，请重新预览' : preview.valid ? '校验通过' : '请修正后重新预览' }}</text>
          <text v-for="cls in preview.classes" :key="cls.class_id" class="help block">{{ cls.class_name }}：{{ cls.before }} → {{ cls.after }} 人</text>
        </view>
        <text class="help block">历史成绩和已发布月评保留原班级；当月未发布月评随档案交接，已有内容和作者保留。</text>
        <text class="field-label">调班原因</text><input v-model="reason" class="field" placeholder="请填写本次调班原因" :maxlength="500" />
        <button class="secondary" :loading="previewing" :disabled="!rows.length || busy" @click="runPreview">预览调整</button>
        <button class="primary" :loading="submitting" :disabled="!fresh || !preview?.valid || !reason.trim() || busy" @click="submit">确认并立即生效</button>
        <text v-if="result" class="success block">批次 #{{ result.id }} 已生效，调整 {{ result.student_count }} 人。</text>
      </view>
    </template>
    <view v-else class="panel">
      <text v-if="!history.items.length" class="help">{{ historyLoading ? '加载中…' : '暂无调班记录' }}</text>
      <view v-for="batch in history.items" :key="batch.id" class="history-batch">
        <text class="h2">批次 #{{ batch.id }} · {{ batch.student_count }} 人</text>
        <text class="help block">{{ formatTime(batch.created_at) }} · {{ batch.actor_name }}</text><text class="help block">{{ batch.reason }}</text>
        <view v-for="item in batch.items" :key="item.student_id" class="transfer-row"><text>{{ item.student_name }} · {{ item.student_username }}</text><text class="help block">{{ item.source_class_name }} → {{ item.target_class_name }}</text></view>
      </view>
      <view class="tabs"><button :disabled="historyPage === 1 || historyLoading" @click="historyPage--; loadHistory()">上一页</button><text>{{ historyPage }}</text><button :disabled="historyPage * 10 >= history.total || historyLoading" @click="historyPage++; loadHistory()">下一页</button></view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import { useAuthStore } from '../../stores/auth'
import { listClasses, listClassStudents, previewTransfers, commitTransfers, listTransfers } from '../api/classes'

const auth = useAuthStore()
const classes = ref([]), source = ref(null), target = ref(null), roster = ref([]), selected = ref([])
const rows = ref([]), preview = ref(null), fresh = ref(false), reason = ref(''), result = ref(null)
const previewing = ref(false), submitting = ref(false), rosterLoading = ref(false), tab = ref('edit')
const history = ref({ items: [], total: 0 }), historyPage = ref(1), historyLoading = ref(false)
let requestId = '', rosterVersion = 0
const busy = computed(() => previewing.value || submitting.value)
const targets = computed(() => classes.value.filter(c => source.value && c.id !== source.value.id && ['school_year', 'education_stage', 'grade', 'class_type', 'short_term_type'].every(k => c[k] === source.value[k])))
watch(rows, () => { fresh.value = false }, { deep: true, flush: 'sync' })
const toast = title => uni.showToast({ title, icon: 'none' })
const sourceName = row => classes.value.find(c => c.id === row.source_class_id)?.name || '自动匹配'
const targetName = row => classes.value.find(c => c.id === row.target_class_id)?.name || '未知班级'
const teacherName = (row, a) => a.options.find(t => t.id === (row.subject_teachers[a.subject] || a.teacher_id))?.name || '请选择'
const formatTime = value => { const d = new Date(new Date(value).getTime() + 8 * 3600000); return d.toISOString().slice(0, 16).replace('T', ' ') }
async function selectSource(event) {
  const version = ++rosterVersion
  source.value = classes.value[Number(event.detail.value)]; target.value = null; roster.value = []; selected.value = []; rosterLoading.value = true
  try { const data = await listClassStudents(source.value.id); if (version === rosterVersion) roster.value = data }
  finally { if (version === rosterVersion) rosterLoading.value = false }
}
function addRows(additions) {
  if (rows.value.length + additions.length > 500) return toast('每批最多500人')
  const seen = new Set(rows.value.map(r => r.student_username))
  for (const row of additions) { if (seen.has(row.student_username)) return toast(`学号${row.student_username}重复`); seen.add(row.student_username) }
  rows.value.push(...additions); preview.value = null; result.value = null
}
function addSelected() { addRows(roster.value.filter(s => selected.value.includes(s.username)).map(s => ({ student_username: s.username, student_name: s.name, source_class_id: source.value.id, target_class_id: target.value.id, subject_teachers: {} }))) }
function removeRow(index) { if (!busy.value) { rows.value.splice(index, 1); preview.value = null } }
function chooseTeacher(index, assignment, event) { rows.value[index].subject_teachers[assignment.subject] = assignment.options[Number(event.detail.value)].id }
async function runPreview() {
  previewing.value = true; fresh.value = false
  const snapshot = JSON.stringify(rows.value)
  try {
    const data = await previewTransfers({ rows: JSON.parse(snapshot) })
    if (JSON.stringify(rows.value) !== snapshot) return
    preview.value = data; fresh.value = true; requestId = `mp_${Date.now()}_${Math.random().toString(36).slice(2)}_${Math.random().toString(36).slice(2)}`
  } catch { fresh.value = false } finally { previewing.value = false }
}
async function submit() {
  const answer = await new Promise(resolve => uni.showModal({ title: '确认批量调班', content: `立即调整${rows.value.length}名学生，并交接当前档案与待办？`, confirmText: '确认生效', success: resolve, fail: () => resolve({ confirm: false }) }))
  if (!answer.confirm || !fresh.value || !preview.value?.valid) return
  submitting.value = true
  try {
    result.value = await commitTransfers({ rows: rows.value, reason: reason.value.trim(), request_id: requestId, preview_token: preview.value.preview_token })
    rows.value = []; preview.value = null; reason.value = ''; roster.value = []; selected.value = []
    uni.showToast({ title: '调班已生效', icon: 'success' })
  } catch (error) { if (error.status === 409) fresh.value = false } finally { submitting.value = false }
}
async function loadHistory() { historyLoading.value = true; try { history.value = await listTransfers({ offset: (historyPage.value - 1) * 10, limit: 10 }) } finally { historyLoading.value = false } }
function showHistory() { tab.value = 'history'; loadHistory() }
onLoad(async () => {
  if (!['admin', 'deyu_director'].includes(auth.role)) { toast('仅德育主任和管理员可调班'); uni.reLaunch({ url: '/pages/index/index' }); return }
  classes.value = (await listClasses()).map(c => ({ ...c, label: `${c.name} · ${c.school_year} · ID ${c.id}` }))
})
</script>

<style scoped>
.page { padding: 28rpx; display: flex; flex-direction: column; gap: 20rpx; color: var(--mp-ink); }
.h1 { font-size: 34rpx; font-weight: 700; }.h2 { display: block; font-size: 30rpx; font-weight: 600; margin-bottom: 16rpx; }
.help { font-size: 25rpx; color: #445269; line-height: 1.6; }.block { display: block; }
.panel { padding: 24rpx; background: #fff; border: 1rpx solid var(--mp-line); border-radius: 12rpx; }
.field { padding: 20rpx; border: 1rpx solid #c6d0de; border-radius: 8rpx; margin: 16rpx 0; min-height: 40rpx; font-size: 28rpx; height: auto; }
.field-label { display: block; margin-top: 20rpx; font-size: 28rpx; }
.student-row { display: flex; gap: 12rpx; padding: 18rpx 0; align-items: center; }
.transfer-row { padding: 20rpx 0; border-bottom: 1rpx solid var(--mp-line); line-height: 1.6; font-size: 28rpx; overflow-wrap: anywhere; }
.row-head { display: flex; justify-content: space-between; gap: 16rpx; }.remove, .error { color: #b42318; }.remove { padding: 0 12rpx; }
.summary { background: var(--mp-soft); padding: 20rpx; margin: 20rpx 0; font-size: 28rpx; }
button { font-size: 28rpx; border-radius: 8rpx; margin-top: 16rpx; }button::after { border: none; }
.primary { background: var(--mp-primary); color: #fff; }.secondary { background: #fff; border: 1rpx solid #c6d0de; color: var(--mp-primary); }
button[disabled] { background: #eef1f5; color: #5c6778; }.tabs { display: flex; align-items: center; gap: 16rpx; }.tabs button { flex: 1; margin-top: 0; background: #fff; }.tabs .active { background: var(--mp-soft); color: var(--mp-primary); font-weight: 600; }
.history-batch + .history-batch { margin-top: 32rpx; }.success { color: #166534; font-size: 28rpx; margin-top: 20rpx; }
</style>
