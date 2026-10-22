<template>
  <div class="page admin-subject-page">
    <div class="page-header"><div><h1 class="page-title">任课老师与班级关联</h1><p class="header-desc">分配班级与学科，教师变动时可直接调整并交接在用方案。</p></div><el-button type="primary" :loading="opening === 'create'" :disabled="!!opening" @click="openCreate">新增关联</el-button></div>
    <div class="table-card">
      <el-input v-model="keyword" class="search-input" aria-label="搜索任课关联" placeholder="搜索班级、学科、老师或账号" clearable />
      <div v-if="loadError" class="load-error" role="alert">任课关联加载失败，请重试。<el-button link type="primary" @click="load">重新加载</el-button></div>
      <el-table class="desktop-links" :data="filteredLinks" v-loading="loading" :empty-text="keyword ? '没有匹配的任课关联' : '暂无任课关联，请先新增关联'">
      <el-table-column prop="class_name" label="班级" min-width="150" />
      <el-table-column prop="subject" label="所带学科" min-width="110" />
      <el-table-column prop="teacher_name" label="任课老师" min-width="140" />
      <el-table-column prop="teacher_username" label="教师账号" min-width="150" />
      <el-table-column label="操作" width="190" fixed="right"><template #default="{ row }"><el-button v-if="canAdjust(row)" link type="primary" :loading="opening === row.id" :disabled="!!opening" @click="openAdjust(row)">调整老师</el-button><el-button link type="danger" :disabled="!!opening" @click="remove(row)">解除关联</el-button></template></el-table-column>
      </el-table>
      <div class="mobile-links" v-loading="loading">
        <p v-if="!filteredLinks.length && !loading" class="empty-links">{{ keyword ? '没有匹配的任课关联' : '暂无任课关联，请先新增关联' }}</p>
        <ul v-else aria-label="任课关联列表">
          <li v-for="row in filteredLinks" :key="row.id">
            <strong>{{ row.class_name }} · {{ row.subject || '班主任' }}</strong>
            <span>{{ row.teacher_name }}</span>
            <span class="teacher-account">{{ row.teacher_username }}</span>
            <div class="mobile-actions"><el-button v-if="canAdjust(row)" link type="primary" :loading="opening === row.id" :disabled="!!opening" @click="openAdjust(row)">调整老师</el-button><el-button link type="danger" :disabled="!!opening" @click="remove(row)">解除关联</el-button></div>
          </li>
        </ul>
      </div>
    </div>
    <el-dialog v-model="visible" title="新增任课关联" width="460px" class="teacher-link-dialog" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving"><el-form label-position="top" :disabled="saving" @submit.prevent="save">
      <el-form-item label="班级" for="link-class"><el-select id="link-class" v-model="form.class_id" filterable placeholder="选择班级" style="width:100%"><el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="任课老师" for="link-teacher"><el-select id="link-teacher" v-model="form.teacher_id" filterable placeholder="选择任课老师" style="width:100%"><el-option v-for="item in createTeachers" :key="item.id" :label="teacherLabel(item)" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="所带学科" for="link-subject"><el-input id="link-subject" v-model="form.subject" placeholder="例如：数学" maxlength="32" clearable style="width:100%" /></el-form-item>
    </el-form><template #footer><el-button :disabled="saving" @click="visible=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存关联</el-button></template></el-dialog>

    <el-dialog v-model="adjustVisible" title="调整任课老师" width="500px" class="teacher-link-dialog" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving">
      <dl class="assignment-summary">
        <div><dt>班级 / 学科</dt><dd>{{ selected?.class_name }} / {{ selected?.subject }}</dd></div>
        <div><dt>原任课老师</dt><dd>{{ selected?.teacher_name }}（{{ selected?.teacher_username }}）</dd></div>
      </dl>
      <p class="handoff-note">确认后，将该班该学科由原老师负责的在用方案交接给接任老师，保留已填写内容。仅交接启用周期中未归档的档案；已归档档案、停用周期和历史月度评定保留原记录。</p>
      <el-form label-position="top" :disabled="saving" @submit.prevent="saveAdjustment">
        <el-form-item label="接任老师" for="adjust-teacher" required>
          <el-select id="adjust-teacher" v-model="adjustForm.teacher_id" aria-label="接任老师" filterable placeholder="选择接任老师" @change="adjustError = ''">
            <el-option v-for="item in replacementTeachers" :key="item.id" :label="teacherLabel(item)" :value="item.id" />
          </el-select>
          <p v-if="!replacementTeachers.length" class="field-note">暂无可选老师，请先启用教师账号；已关联本班该学科的老师无需重复关联。</p>
        </el-form-item>
        <el-form-item label="调整原因（选填）" for="adjust-reason"><el-input id="adjust-reason" v-model="adjustForm.reason" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="例如：本学期教学安排调整" /></el-form-item>
      </el-form>
      <p v-if="adjustError" class="adjust-error" role="alert">{{ adjustError }}</p>
      <template #footer><el-button :disabled="saving" @click="adjustVisible = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!adjustForm.teacher_id" @click="saveAdjustment">确认调整</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adjustClassTeacherLink, createClassTeacherLink, deleteClassTeacherLink, listClassTeacherLinks } from '../../api/admin'
import { listClasses } from '../../api/classes'
import { listUsers } from '../../api/users'
const links = ref([]); const teachers = ref([]); const classes = ref([]); const loading = ref(false); const visible = ref(false)
const loadError = ref(false); const opening = ref(null); const saving = ref(false); const keyword = ref('')
const selected = ref(null); const adjustVisible = ref(false); const adjustError = ref('')
const form = reactive({ class_id: null, teacher_id: null, subject: '' })
const adjustForm = reactive({ teacher_id: null, reason: '' })
const createTeachers = computed(() => teachers.value.filter(item => item.role === 'subject_teacher'))
const filteredLinks = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return links.value.filter(row => !query || [row.class_name, row.subject, row.teacher_name, row.teacher_username].some(value => String(value || '').toLowerCase().includes(query)))
})
const replacementTeachers = computed(() => {
  const row = selected.value
  if (!row) return []
  const existingIds = new Set(links.value.filter(item => item.class_id === row.class_id && item.subject === row.subject).map(item => item.teacher_id))
  return teachers.value.filter(item => item.id !== row.teacher_id && !existingIds.has(item.id))
})
const teacherLabel = item => `${item.name}（${item.username}）${item.role === 'teacher' ? ' · 班主任兼课' : ''}`
const canAdjust = row => row.role === 'subject_teacher' && row.subject?.trim() && row.subject.trim() !== '德育'
async function load() {
  loading.value = true; loadError.value = false
  try { links.value = await listClassTeacherLinks() }
  catch { loadError.value = true }
  finally { loading.value = false }
}
async function fetchTeacherRole(role) {
  const all = []
  // 教师名单也有分页，避免超过默认 200 人后接任老师无法选择。
  for (let offset = 0; ; offset += 500) {
    const page = await listUsers(role, '', { limit: 500, offset })
    all.push(...page)
    if (page.length < 500) return all
  }
}
async function loadTeachers() {
  const groups = await Promise.all([fetchTeacherRole('subject_teacher'), fetchTeacherRole('teacher')])
  teachers.value = groups.flat().filter(item => item.status === 'active')
}
async function openCreate() {
  opening.value = 'create'
  Object.assign(form, { class_id: null, teacher_id: null, subject: '' })
  try {
    const [, rows] = await Promise.all([loadTeachers(), listClasses()])
    classes.value = rows; visible.value = true
  } catch { /* 请求错误由统一拦截器提示。 */ }
  finally { opening.value = null }
}
async function openAdjust(row) {
  opening.value = row.id; selected.value = { ...row }
  Object.assign(adjustForm, { teacher_id: null, reason: '' }); adjustError.value = ''
  try { await loadTeachers(); adjustVisible.value = true }
  catch { /* 请求错误由统一拦截器提示。 */ }
  finally { opening.value = null }
}
async function save() {
  if (saving.value) return
  if (!form.class_id || !form.teacher_id || !form.subject.trim()) return ElMessage.warning('请选择班级、任课老师并填写学科')
  saving.value = true
  try {
    await createClassTeacherLink({ class_id: form.class_id, teacher_id: form.teacher_id, subject: form.subject.trim() })
    ElMessage.success('任课关联已建立'); visible.value = false; await load()
  } catch { /* 保留表单，方便修正后重试。 */ }
  finally { saving.value = false }
}
async function saveAdjustment() {
  if (saving.value || !selected.value || !adjustForm.teacher_id) return
  saving.value = true; adjustError.value = ''
  try {
    const result = await adjustClassTeacherLink(selected.value.id, {
      teacher_id: adjustForm.teacher_id, previous_teacher_id: selected.value.teacher_id, reason: adjustForm.reason.trim(),
    })
    links.value = links.value.map(row => row.id === result.id ? result : row)
    adjustVisible.value = false
    ElMessage.success(`任课老师已调整，已交接 ${result.updated_plans} 份在用学科方案`)
    await load()
  } catch (error) { adjustError.value = error.response?.data?.detail || '调整失败，请稍后重试' }
  finally { saving.value = false }
}
async function remove(row) {
  try { await ElMessageBox.confirm(`确认解除「${row.teacher_name}」在「${row.class_name}」的「${row.subject}」任课关联？`, '解除关联', { type: 'warning' }) }
  catch { return }
  try { await deleteClassTeacherLink(row.id); ElMessage.success('关联已解除'); await load() }
  catch { /* 请求错误由统一拦截器提示。 */ }
}
onMounted(load)
</script>
<style scoped>
.admin-subject-page{display:flex;flex-direction:column;gap:20px;min-width:0}
.page-header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.page-title{margin:0 0 4px;font-size:var(--font-size-page-title);color:var(--ink)}
.header-desc{margin:0;color:#445269;font-size:13.5px;line-height:1.6}
.table-card{min-width:0;background:#fff;border:1px solid #e2e8f0;border-radius:var(--radius);padding:16px 18px}
.search-input{max-width:360px;margin-bottom:16px}
.mobile-links{display:none}
.load-error,.adjust-error{color:#b42318;font-size:14px;line-height:1.6}
.assignment-summary{margin:0;display:flex;flex-direction:column;gap:12px}
.assignment-summary>div{display:grid;grid-template-columns:100px minmax(0,1fr);gap:12px}
.assignment-summary dt{color:#445269}
.assignment-summary dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.handoff-note{margin:20px 0;color:#445269;line-height:1.7}
.field-note{margin:6px 0 0;color:#445269;font-size:13px;line-height:1.6}
.teacher-link-dialog :deep(.el-select){width:100%}
@media(max-width:600px){
  .page-header{flex-wrap:wrap}.table-card{padding:12px;overflow:hidden}.assignment-summary>div{grid-template-columns:1fr;gap:4px}
  .desktop-links{display:none}.mobile-links{display:block;min-height:64px}
  .mobile-links ul{list-style:none;padding:0;margin:0}
  .mobile-links li{display:flex;flex-direction:column;gap:6px;padding:14px 0;border-bottom:1px solid #e5eaf2;overflow-wrap:anywhere}
  .mobile-links li:last-child{border-bottom:0;padding-bottom:0}
  .mobile-links strong{font-weight:600;color:var(--ink)}
  .teacher-account,.empty-links{font-size:13px;color:#445269}
  .mobile-actions{display:flex;gap:16px}.mobile-actions :deep(.el-button){min-height:36px;margin:0}
}
</style>
<style>
.el-dialog.teacher-link-dialog{max-width:calc(100vw - 32px)}
</style>
