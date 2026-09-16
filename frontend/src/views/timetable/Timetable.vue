<template>
  <section class="page timetable-page">
    <header class="page-header">
      <div>
        <h1>{{ canSchedule ? '全校课表编排' : '我的课程安排' }}</h1>
        <p>{{ canSchedule ? '按班级和教师维护每周固定课程；系统会阻止班级或教师撞课。' : '这里展示已安排给您的每周固定课程。' }}</p>
      </div>
      <el-button v-if="canSchedule" type="primary" :icon="Plus" @click="openCreate">新增课程</el-button>
    </header>

    <div v-if="canSchedule" class="filters">
      <el-select v-model="filters.class_id" clearable filterable placeholder="全部班级" @change="load"><el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" /></el-select>
      <el-select v-model="filters.teacher_id" clearable filterable placeholder="全部任课老师" @change="load"><el-option v-for="item in teachers" :key="item.id" :label="teacherLabel(item)" :value="item.id" /></el-select>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="schedule-card" v-loading="loading">
      <div class="schedule-title">
        <div><strong>{{ canSchedule ? '周课表' : '个人周课表' }}</strong><span v-if="canSchedule" class="schedule-tip">点击空白格可直接排课</span></div>
        <div class="schedule-summary">
          <span class="schedule-field"><b>班级</b>{{ selectedClass?.name || '全部班级' }}</span>
          <span class="schedule-field selected-room"><b>班级教室</b>{{ selectedClassroom || '全部教室' }}</span>
          <span>共 {{ entries.length }} 节课</span>
        </div>
      </div>
      <div v-if="canSchedule" class="timetable-grid-wrap">
        <table class="timetable-grid">
          <thead><tr><th class="period-heading">节次</th><th v-for="day in weekdays" :key="day.value">{{ day.short }}</th></tr></thead>
          <tbody>
            <tr v-for="period in periodRows" :key="period">
              <th scope="row" class="period-cell">
                <strong>第 {{ period }} 节</strong>
                <template v-if="canSchedule && editingPeriod === period">
                  <input v-model="periodForm.start_time" class="period-time-input" type="time" aria-label="开始时间" @click.stop>
                  <input v-model="periodForm.end_time" class="period-time-input" type="time" aria-label="结束时间" @click.stop>
                  <div class="period-edit-actions"><el-button link type="primary" size="small" :loading="periodSaving" @click.stop="savePeriod(period)">保存</el-button><el-button link size="small" @click.stop="cancelPeriodEdit">取消</el-button></div>
                </template>
                <template v-else>
                  <span>{{ getPeriodTime(period) || '时间未配置' }}</span>
                  <el-button v-if="canSchedule" link type="primary" size="small" class="period-edit-trigger" @click.stop="startPeriodEdit(period)">修改时间</el-button>
                </template>
              </th>
              <td v-for="day in weekdays" :key="day.value" :class="['course-cell', { 'has-course': entryAt(day.value, period) }]" @click="openCell(day.value, period)">
                <template v-if="entryAt(day.value, period)">
                  <div class="course-subject">{{ entryAt(day.value, period).subject }}</div>
                  <div class="course-meta">{{ entryAt(day.value, period).teacher_name }}</div>
                  <div class="course-actions" @click.stop><el-button link type="primary" size="small" @click="openEdit(entryAt(day.value, period))">编辑</el-button><el-button link type="danger" size="small" @click="remove(entryAt(day.value, period))">删除</el-button></div>
                </template>
                <button v-else class="empty-slot" type="button" aria-label="新增课程"><span>＋</span><small>排课</small></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <el-table v-else :data="entries" empty-text="暂无课程安排" :default-sort="{ prop: 'weekday', order: 'ascending' }">
        <el-table-column label="星期" prop="weekday" width="100" sortable><template #default="{ row }">{{ weekdayLabel(row.weekday) }}</template></el-table-column>
        <el-table-column label="节次" prop="period" width="90" sortable><template #default="{ row }">第 {{ row.period }} 节</template></el-table-column>
        <el-table-column label="上课时间" width="130"><template #default="{ row }"><span v-if="row.start_time">{{ row.start_time }}-{{ row.end_time }}</span><span v-else class="text-muted">未配置</span></template></el-table-column>
        <el-table-column prop="subject" label="课程" min-width="130"><template #default="{ row }"><strong>{{ row.subject }}</strong></template></el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column v-if="canSchedule" prop="teacher_name" label="授课教师" min-width="130" />
        <el-table-column label="上课地点" min-width="130"><template #default="{ row }">{{ row.classroom || '未填写' }}</template></el-table-column>
        <el-table-column v-if="canSchedule" label="操作" width="140" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑课程' : '新增课程'" width="500px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="班级" required><el-select v-model="form.class_id" filterable placeholder="选择班级" style="width:100%"><el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="授课老师" required><el-select v-model="form.teacher_id" filterable placeholder="选择任课老师" style="width:100%"><el-option v-for="item in teachers" :key="item.id" :label="teacherLabel(item)" :value="item.id" /></el-select></el-form-item>
        <div class="form-grid"><el-form-item label="课程名称" required><el-input v-model="form.subject" placeholder="如：数学" /></el-form-item><el-form-item label="上课地点"><el-input v-model="form.classroom" placeholder="如：201教室" /></el-form-item></div>
        <div class="form-grid"><el-form-item label="星期" required><el-select v-model="form.weekday"><el-option v-for="day in weekdays" :key="day.value" :label="day.label" :value="day.value" /></el-select></el-form-item><el-form-item label="节次" required><el-input-number v-model="form.period" :min="1" :max="12" style="width:100%" /><div class="period-time-hint" v-if="getPeriodTime(form.period)">{{ getPeriodTime(form.period) }}</div></el-form-item></div>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'
import { listClasses, listUsers } from '../../api/classes'
import { createTimetableEntry, deleteTimetableEntry, listTimetable, myTimetable, updateTimetableEntry } from '../../api/timetables'
import { listPeriodTimes, updatePeriodTime } from '../../api/period_times'

const auth = useAuthStore()
const canSchedule = computed(() => ['admin', 'deyu_director'].includes(auth.role))
const entries = ref([]), classes = ref([]), teachers = ref([]), periodTimesMap = ref({}), loading = ref(false), saving = ref(false), periodSaving = ref(false), dialogVisible = ref(false), editingId = ref(null), editingPeriod = ref(null)
const filters = reactive({ class_id: null, teacher_id: null })
const form = reactive({ class_id: null, teacher_id: null, subject: '', weekday: 1, period: 1, classroom: '' })
const periodForm = reactive({ start_time: '', end_time: '' })
const weekdays = [{ value: 1, label: '星期一', short: '周一' }, { value: 2, label: '星期二', short: '周二' }, { value: 3, label: '星期三', short: '周三' }, { value: 4, label: '星期四', short: '周四' }, { value: 5, label: '星期五', short: '周五' }, { value: 6, label: '星期六', short: '周六' }, { value: 7, label: '星期日', short: '周日' }]
const weekdayLabel = (value) => weekdays.find(day => day.value === value)?.label || `星期${value}`
const teacherLabel = (teacher) => teacher.subject ? `${teacher.name}（${teacher.subject}）` : teacher.name
const selectedClass = computed(() => classes.value.find(item => item.id === filters.class_id) || null)
const selectedClassroom = computed(() => {
  const rooms = [...new Set(entries.value.map(item => item.classroom).filter(Boolean))]
  return selectedClass.value ? rooms.join('、') : ''
})
const getPeriodTime = (period) => {
  const pt = periodTimesMap.value[period]
  return pt ? `${pt.start_time}-${pt.end_time}` : ''
}
const periodRows = computed(() => {
  const periods = new Set([...Object.keys(periodTimesMap.value).map(Number), ...entries.value.map(item => item.period)])
  return (periods.size ? [...periods] : Array.from({ length: 8 }, (_, index) => index + 1)).sort((a, b) => a - b)
})
const entryAt = (weekday, period) => entries.value.find(item => item.weekday === weekday && item.period === period)

async function load() {
  loading.value = true
  try { entries.value = canSchedule.value ? await listTimetable(filters) : await myTimetable() }
  finally { loading.value = false }
}
async function loadOptions() {
  // 节次时间是展示增强项，旧服务未升级或迁移未执行时也不能阻断班级下拉框。
  const tasks = [listPeriodTimes()]
  if (canSchedule.value) tasks.push(listClasses(), listUsers('subject_teacher'))
  const [periodResult, classResult, subjectsResult] = await Promise.allSettled(tasks)
  if (periodResult.status === 'fulfilled') {
    const map = {}
    periodResult.value.forEach(pt => { map[pt.period] = pt })
    periodTimesMap.value = map
  }
  if (!canSchedule.value) return
  if (classResult?.status === 'fulfilled') classes.value = classResult.value
  if (subjectsResult?.status === 'fulfilled') teachers.value = subjectsResult.value
}
function openCreate() { editingId.value = null; Object.assign(form, { class_id: null, teacher_id: null, subject: '', weekday: 1, period: 1, classroom: '' }); dialogVisible.value = true }
function openCell(weekday, period) { if (!entryAt(weekday, period)) { editingId.value = null; Object.assign(form, { class_id: filters.class_id || null, teacher_id: filters.teacher_id || null, subject: '', weekday, period, classroom: '' }); dialogVisible.value = true } }
function openEdit(row) { editingId.value = row.id; Object.assign(form, { class_id: row.class_id, teacher_id: row.teacher_id, subject: row.subject, weekday: row.weekday, period: row.period, classroom: row.classroom || '' }); dialogVisible.value = true }
function startPeriodEdit(period) { const current = periodTimesMap.value[period]; if (!current) return ElMessage.warning('请先配置该节次时间'); editingPeriod.value = period; Object.assign(periodForm, { start_time: current.start_time, end_time: current.end_time }) }
function cancelPeriodEdit() { editingPeriod.value = null }
async function savePeriod(period) {
  if (!periodForm.start_time || !periodForm.end_time || periodForm.start_time >= periodForm.end_time) return ElMessage.warning('结束时间必须晚于开始时间')
  periodSaving.value = true
  try { periodTimesMap.value[period] = await updatePeriodTime(period, periodForm); editingPeriod.value = null; ElMessage.success('节次时间已更新') }
  finally { periodSaving.value = false }
}
async function save() {
  if (!form.class_id || !form.teacher_id || !form.subject.trim()) return ElMessage.warning('请完整填写班级、授课教师和课程名称')
  saving.value = true
  try { if (editingId.value) await updateTimetableEntry(editingId.value, form); else await createTimetableEntry(form); ElMessage.success('课程已保存'); dialogVisible.value = false; await load() }
  finally { saving.value = false }
}
async function remove(row) { try { await ElMessageBox.confirm(`确认删除「${weekdayLabel(row.weekday)}第${row.period}节 ${row.subject}」？`, '删除课程', { type: 'warning' }); await deleteTimetableEntry(row.id); ElMessage.success('课程已删除'); await load() } catch {} }
onMounted(async () => { await Promise.all([loadOptions(), load()]) })
</script>

<style scoped>
.timetable-page { display:flex; flex-direction:column; gap:18px; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
h1 { margin:0 0 6px; color:var(--ink); font-size:22px; } p { margin:0; color:#64748b; font-size:13.5px; }
.filters, .schedule-card { background:#fff; border:1px solid #cbd5e1; border-radius:var(--radius); padding:14px 18px; }
.filters { display:flex; flex-wrap:wrap; gap:10px; }.filters .el-select { width:200px; }
.schedule-card { padding:0; overflow:hidden; }.schedule-title { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 16px; border-bottom:1px solid #cbd5e1; color:var(--ink); }.schedule-title span { color:#64748b; font-size:12px; }.schedule-title > div { display:flex; align-items:center; gap:12px; }.schedule-tip { color:#64748b; }.schedule-summary { justify-content:flex-end; }.schedule-field { display:flex; align-items:center; gap:5px; color:#475569 !important; }.schedule-field b { color:#123a64; font-weight: var(--font-weight-heading); }.selected-room { padding-left:12px; border-left:1px solid #cbd5e1; }
.timetable-grid-wrap { overflow:auto; background:#fff; }
.timetable-grid { width:100%; min-width:980px; border-collapse:separate; border-spacing:0; table-layout:fixed; }
.timetable-grid th { height:38px; color:#475569; background:#f1f5f9; font-size:13px; font-weight: var(--font-weight-heading); text-align:center; border-bottom:1px solid #cbd5e1; border-right:1px solid #cbd5e1; }.timetable-grid th:last-child { border-right:0; }
.timetable-grid .period-heading { width:112px; }
.timetable-grid td { height:104px; padding:7px 8px; vertical-align:top; border-right:1px solid #cbd5e1; border-bottom:1px solid #cbd5e1; background:#fff; }.timetable-grid td:last-child { border-right:0; }.timetable-grid tbody tr:last-child td { border-bottom:0; }
.timetable-grid .period-cell { width:112px; padding:8px 6px; vertical-align:middle; }.period-cell strong, .period-cell span { display:block; }.period-cell strong { color:#334155; font-size:13px; }.period-cell span { margin-top:2px; color:#64748b; font-size:11px; font-weight:400; }.period-edit-trigger { height:auto; margin-top:2px; padding:0; font-size:11px; }.period-time-input { box-sizing:border-box; width:98px; height:22px; margin-top:3px; padding:1px 3px; color:#334155; background:#fff; border:1px solid #94a3b8; border-radius:3px; font-size:11px; }.period-edit-actions { display:flex; justify-content:center; gap:6px; margin-top:2px; }.period-edit-actions .el-button { height:auto; padding:0; font-size:11px; }
.course-cell { cursor:pointer; transition:background-color .16s ease; }.course-cell:hover { background:#f8fafc; }.course-cell.has-course { background:#f7faff; }
.course-subject { overflow:hidden; color:#123a64; font-size:13.5px; font-weight: var(--font-weight-heading); line-height:19px; text-overflow:ellipsis; white-space:nowrap; }.course-meta { overflow:hidden; margin-top:2px; color:#475569; font-size:12px; line-height:16px; text-overflow:ellipsis; white-space:nowrap; }.course-actions { display:flex; gap:8px; margin-top:5px; }.course-actions .el-button { padding:0; font-size:12px; }
.empty-slot { display:flex; width:100%; height:100%; min-height:82px; align-items:center; justify-content:center; gap:5px; color:#94a3b8; background:transparent; border:0; cursor:pointer; font:inherit; opacity:0; transition:opacity .16s ease, color .16s ease; }.empty-slot span { font-size:16px; line-height:1; }.empty-slot small { font-size:12px; }.course-cell:hover .empty-slot, .empty-slot:focus-visible { opacity:1; color:#2563a8; outline:0; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.period-time-hint { margin-top:4px; font-size:12px; color:#64748b; }
.text-muted { color:#94a3b8; font-size:12px; }
@media (prefers-reduced-motion: reduce) { .course-cell, .empty-slot { transition:none; } }
@media (max-width: 680px) { .page-header { display:grid; }.form-grid { grid-template-columns:1fr; }.schedule-title > div { align-items:flex-start; flex-direction:column; gap:3px; } }
</style>
