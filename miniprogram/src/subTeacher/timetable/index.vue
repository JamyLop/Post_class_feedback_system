<template>
  <view class="page">
    <WorkspaceLink />
    <view class="head"><text class="h1">{{ isScheduler ? '课表编排' : '我的课表' }}</text><text class="p">{{ isScheduler ? '为班级安排固定周课表，系统会自动拦截撞课。' : '查看德育主任安排给您的每周课程。' }}</text></view>

    <view v-if="isScheduler" class="card">
      <view class="card-head"><text class="card-title">{{ editingId ? '编辑课程' : '新增课程' }}</text><text v-if="editingId" class="link" @click="resetForm">取消编辑</text></view>
      <view class="form">
        <view class="field"><text class="label">班级 <text class="required">*</text></text><picker :range="classOptions" range-key="name" :value="classIndex" @change="onClassChange"><view class="picker"><text>{{ classLabel }}</text><text>⌄</text></view></picker></view>
        <view class="field"><text class="label">授课教师 <text class="required">*</text></text><picker :range="teacherOptions" range-key="label" :value="teacherIndex" @change="onTeacherChange"><view class="picker"><text>{{ teacherLabel }}</text><text>⌄</text></view></picker><text class="hint">仅可保存已分配到该班级的班主任或任课老师。</text></view>
        <view class="field"><text class="label">课程名称 <text class="required">*</text></text><input v-model="form.subject" class="input" placeholder="如：数学" /></view>
        <view class="two"><view class="field"><text class="label">星期 <text class="required">*</text></text><picker :range="weekdays" range-key="label" :value="weekdayIndex" @change="onWeekdayChange"><view class="picker"><text>{{ weekdayLabel }}</text><text>⌄</text></view></picker></view><view class="field"><text class="label">节次 <text class="required">*</text></text><picker :range="periodOptions" :value="periodIndex" @change="onPeriodChange"><view class="picker"><text>第 {{ form.period }} 节</text><text>⌄</text></view></picker></view></view>
        <view class="field"><text class="label">上课地点</text><input v-model="form.classroom" class="input" placeholder="如：201教室" /></view>
        <button class="btn-primary" :loading="saving" :disabled="saving" @click="save">{{ editingId ? '保存修改' : '保存排课' }}</button>
      </view>
    </view>

    <view class="list-head"><text>{{ isScheduler ? '全校课程安排' : '本周课程安排' }}</text><button class="btn-refresh" :loading="loading" @click="loadData">刷新</button></view>
    <view v-if="loading" class="loading">加载中...</view>
    <EmptyState v-else-if="!rows.length" title="暂无课程安排" :desc="isScheduler ? '填写上方表单后即可新增第一节课程' : '德育主任尚未为您排课'" />
    <view v-else class="list"><view v-for="row in rows" :key="row.id" class="course-card"><view class="course-main"><text class="course">{{ row.subject }}</text><text class="meta">{{ weekday(row.weekday) }} · 第{{ row.period }}节 · {{ row.class_name }}</text><text class="meta">{{ row.teacher_name }}<text v-if="row.classroom"> · {{ row.classroom }}</text></text></view><view v-if="isScheduler" class="actions"><text class="link" @click="startEdit(row)">编辑</text><text class="delete" @click="remove(row)">删除</text></view></view></view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import WorkspaceLink from '../../components/WorkspaceLink.vue'
import EmptyState from '../../components/EmptyState.vue'
import { useAuthStore } from '../../stores/auth'
import { createTimetableEntry, deleteTimetableEntry, listClasses, listTimetable, listUsers, myTimetable, updateTimetableEntry } from '../../api/classes'

const auth = useAuthStore()
const isScheduler = computed(() => ['admin', 'deyu_director'].includes(auth.role))
const loading = ref(false), saving = ref(false), rows = ref([]), editingId = ref(null)
const classOptions = ref([{ id: null, name: '请选择班级' }])
const teacherOptions = ref([{ id: null, label: '请选择授课教师' }])
const weekdays = [{ value: 1, label: '星期一' }, { value: 2, label: '星期二' }, { value: 3, label: '星期三' }, { value: 4, label: '星期四' }, { value: 5, label: '星期五' }, { value: 6, label: '星期六' }, { value: 7, label: '星期日' }]
const periodOptions = Array.from({ length: 12 }, (_, index) => index + 1)
const form = reactive({ class_id: null, teacher_id: null, subject: '', weekday: 1, period: 1, classroom: '' })
const classIndex = computed(() => Math.max(0, classOptions.value.findIndex(item => item.id === form.class_id)))
const teacherIndex = computed(() => Math.max(0, teacherOptions.value.findIndex(item => item.id === form.teacher_id)))
const weekdayIndex = computed(() => Math.max(0, weekdays.findIndex(item => item.value === form.weekday)))
const periodIndex = computed(() => Math.max(0, periodOptions.indexOf(form.period)))
const classLabel = computed(() => classOptions.value[classIndex.value]?.name || '请选择班级')
const teacherLabel = computed(() => teacherOptions.value[teacherIndex.value]?.label || '请选择授课教师')
const weekdayLabel = computed(() => weekdays[weekdayIndex.value]?.label || '星期一')
const weekday = value => weekdays.find(item => item.value === value)?.label || `星期${value}`
function onClassChange(e) { form.class_id = classOptions.value[Number(e.detail.value)]?.id || null }
function onTeacherChange(e) { const item = teacherOptions.value[Number(e.detail.value)]; form.teacher_id = item?.id || null; if (!form.subject && item?.subject) form.subject = item.subject }
function onWeekdayChange(e) { form.weekday = weekdays[Number(e.detail.value)]?.value || 1 }
function onPeriodChange(e) { form.period = periodOptions[Number(e.detail.value)] || 1 }
async function loadOptions() {
  if (!isScheduler.value) return
  const [classes, headTeachers, subjectTeachers] = await Promise.all([listClasses(), listUsers('teacher', ''), listUsers('subject_teacher', '')])
  classOptions.value = [{ id: null, name: '请选择班级' }, ...(classes || [])]
  const teachers = [...(headTeachers || []), ...(subjectTeachers || [])]
  teacherOptions.value = [{ id: null, label: '请选择授课教师' }, ...teachers.map(item => ({ id: item.id, subject: item.subject || '', label: `${item.name}（${item.role === 'teacher' ? '班主任' : '任课老师'}）` }))]
}
async function loadData() { loading.value = true; try { rows.value = isScheduler.value ? await listTimetable() : await myTimetable() } catch (_) { rows.value = [] } finally { loading.value = false } }
function resetForm() { editingId.value = null; Object.assign(form, { class_id: null, teacher_id: null, subject: '', weekday: 1, period: 1, classroom: '' }) }
function startEdit(row) { editingId.value = row.id; Object.assign(form, { class_id: row.class_id, teacher_id: row.teacher_id, subject: row.subject, weekday: row.weekday, period: row.period, classroom: row.classroom || '' }); uni.pageScrollTo({ scrollTop: 0, duration: 200 }) }
async function save() { if (!form.class_id || !form.teacher_id || !form.subject.trim()) return uni.showToast({ title: '请完整填写班级、教师和课程名称', icon: 'none' }); saving.value = true; try { const payload = { ...form, subject: form.subject.trim(), classroom: form.classroom.trim() }; if (editingId.value) await updateTimetableEntry(editingId.value, payload); else await createTimetableEntry(payload); uni.showToast({ title: '课表已保存', icon: 'success' }); resetForm(); await loadData() } catch (_) {} finally { saving.value = false } }
function remove(row) { uni.showModal({ title: '删除课程', content: `确认删除“${weekday(row.weekday)}第${row.period}节 ${row.subject}”吗？`, success: async ({ confirm }) => { if (!confirm) return; try { await deleteTimetableEntry(row.id); uni.showToast({ title: '已删除', icon: 'success' }); await loadData() } catch (_) {} } }) }
function guardRole() { if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return false }; if (!['teacher', 'subject_teacher', 'deyu_director', 'admin'].includes(auth.role)) { uni.showToast({ title: '当前角色无权限', icon: 'none' }); return false }; return true }
onShow(async () => { if (!guardRole()) return; try { await loadOptions() } catch (_) { uni.showToast({ title: '课表基础数据加载失败', icon: 'none' }) }; await loadData() })
</script>

<style scoped>
.page { padding:28rpx; padding-bottom:48rpx; display:flex; flex-direction:column; gap:20rpx; }.h1 { display:block; color:var(--mp-ink); font-size:34rpx; font-weight:700; }.p,.meta,.hint { display:block; color:var(--mp-muted); font-size:24rpx; margin-top:6rpx; }.card,.course-card { background:#fff; border:1rpx solid var(--mp-line); border-radius:12rpx; padding:24rpx; }.card-head,.list-head { display:flex; align-items:center; justify-content:space-between; }.card-title,.list-head > text { color:var(--mp-ink); font-size:28rpx; font-weight:600; }.link { color:var(--mp-primary); font-size:24rpx; }.form { display:flex; flex-direction:column; gap:18rpx; margin-top:20rpx; }.field { display:flex; flex:1; flex-direction:column; gap:8rpx; }.two { display:flex; gap:16rpx; }.label { color:var(--mp-body); font-size:24rpx; }.required,.delete { color:#a33e39; }.picker,.input { display:flex; align-items:center; justify-content:space-between; min-height:42rpx; padding:16rpx 20rpx; color:var(--mp-ink); background:#fff; border:1rpx solid #c6d0de; border-radius:8rpx; font-size:28rpx; }.hint { font-size:22rpx; }.btn-primary { margin-top:4rpx; color:#fff; background:var(--mp-primary); border:0; border-radius:8rpx; font-size:29rpx; font-weight:600; }.btn-primary::after,.btn-refresh::after { border:0; }.btn-refresh { margin:0; padding:8rpx 20rpx; color:var(--mp-primary); background:#fff; border:1rpx solid #c6d0de; border-radius:8rpx; font-size:24rpx; }.loading { padding:48rpx; color:var(--mp-muted); text-align:center; }.list { display:flex; flex-direction:column; gap:14rpx; }.course-card { display:flex; align-items:center; justify-content:space-between; }.course-main { flex:1; }.course { display:block; color:var(--mp-ink); font-size:29rpx; font-weight:600; }.actions { display:flex; flex-direction:column; gap:14rpx; align-items:flex-end; margin-left:20rpx; }
</style>
