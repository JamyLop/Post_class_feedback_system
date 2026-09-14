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
      <el-select v-model="filters.teacher_id" clearable filterable placeholder="全部教师" @change="load"><el-option v-for="item in teachers" :key="item.id" :label="teacherLabel(item)" :value="item.id" /></el-select>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="schedule-card" v-loading="loading">
      <div class="schedule-title"><strong>{{ canSchedule ? '周课表' : '个人周课表' }}</strong><span>共 {{ entries.length }} 节课</span></div>
      <el-table :data="entries" empty-text="暂无课程安排" :default-sort="{ prop: 'weekday', order: 'ascending' }">
        <el-table-column label="星期" prop="weekday" width="100" sortable><template #default="{ row }">{{ weekdayLabel(row.weekday) }}</template></el-table-column>
        <el-table-column label="节次" prop="period" width="90" sortable><template #default="{ row }">第 {{ row.period }} 节</template></el-table-column>
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
        <el-form-item label="授课教师" required><el-select v-model="form.teacher_id" filterable placeholder="仅可选择已分配到班级的教师" style="width:100%"><el-option v-for="item in teachers" :key="item.id" :label="teacherLabel(item)" :value="item.id" /></el-select></el-form-item>
        <div class="form-grid"><el-form-item label="课程名称" required><el-input v-model="form.subject" placeholder="如：数学" /></el-form-item><el-form-item label="上课地点"><el-input v-model="form.classroom" placeholder="如：201教室" /></el-form-item></div>
        <div class="form-grid"><el-form-item label="星期" required><el-select v-model="form.weekday"><el-option v-for="day in weekdays" :key="day.value" :label="day.label" :value="day.value" /></el-select></el-form-item><el-form-item label="节次" required><el-input-number v-model="form.period" :min="1" :max="12" style="width:100%" /></el-form-item></div>
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

const auth = useAuthStore()
const canSchedule = computed(() => ['admin', 'deyu_director'].includes(auth.role))
const entries = ref([]), classes = ref([]), teachers = ref([]), loading = ref(false), saving = ref(false), dialogVisible = ref(false), editingId = ref(null)
const filters = reactive({ class_id: null, teacher_id: null })
const form = reactive({ class_id: null, teacher_id: null, subject: '', weekday: 1, period: 1, classroom: '' })
const weekdays = [{ value: 1, label: '星期一' }, { value: 2, label: '星期二' }, { value: 3, label: '星期三' }, { value: 4, label: '星期四' }, { value: 5, label: '星期五' }, { value: 6, label: '星期六' }, { value: 7, label: '星期日' }]
const weekdayLabel = (value) => weekdays.find(day => day.value === value)?.label || `星期${value}`
const teacherLabel = (teacher) => `${teacher.name}（${teacher.role === 'teacher' ? '班主任' : '任课老师'}）`

async function load() {
  loading.value = true
  try { entries.value = canSchedule.value ? await listTimetable(filters) : await myTimetable() }
  finally { loading.value = false }
}
async function loadOptions() {
  if (!canSchedule.value) return
  const [classRows, heads, subjects] = await Promise.all([listClasses(), listUsers('teacher'), listUsers('subject_teacher')])
  classes.value = classRows
  teachers.value = [...heads, ...subjects]
}
function openCreate() { editingId.value = null; Object.assign(form, { class_id: null, teacher_id: null, subject: '', weekday: 1, period: 1, classroom: '' }); dialogVisible.value = true }
function openEdit(row) { editingId.value = row.id; Object.assign(form, { class_id: row.class_id, teacher_id: row.teacher_id, subject: row.subject, weekday: row.weekday, period: row.period, classroom: row.classroom || '' }); dialogVisible.value = true }
async function save() {
  if (!form.class_id || !form.teacher_id || !form.subject.trim()) return ElMessage.warning('请完整填写班级、授课教师和课程名称')
  saving.value = true
  try { if (editingId.value) await updateTimetableEntry(editingId.value, form); else await createTimetableEntry(form); ElMessage.success('课程已保存'); dialogVisible.value = false; await load() }
  finally { saving.value = false }
}
async function remove(row) { try { await ElMessageBox.confirm(`确认删除「${weekdayLabel(row.weekday)}第${row.period}节 ${row.subject}」？`, '删除课程', { type: 'warning' }); await deleteTimetableEntry(row.id); ElMessage.success('课程已删除'); await load() } catch {} }
onMounted(async () => { await loadOptions(); await load() })
</script>

<style scoped>
.timetable-page { display:flex; flex-direction:column; gap:18px; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
h1 { margin:0 0 6px; color:var(--ink); font-size:22px; } p { margin:0; color:#64748b; font-size:13.5px; }
.filters, .schedule-card { background:#fff; border:1px solid #e2e8f0; border-radius:var(--radius); padding:14px 18px; }
.filters { display:flex; flex-wrap:wrap; gap:10px; }.filters .el-select { width:200px; }
.schedule-card { padding:0; overflow:hidden; }.schedule-title { display:flex; justify-content:space-between; padding:15px 18px; border-bottom:1px solid #e2e8f0; color:var(--ink); }.schedule-title span { color:#64748b; font-size:12px; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width: 680px) { .page-header { display:grid; }.form-grid { grid-template-columns:1fr; } }
</style>
