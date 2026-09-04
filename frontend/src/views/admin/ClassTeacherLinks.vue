<template>
  <div class="page admin-subject-page">
    <div class="page-header"><div><h1 class="page-title">任课老师与班级关联</h1><p class="header-desc">为任课老师分配所带班级与学科，任课端只展示其所带学科班级的科目方案。</p></div><el-button type="primary" @click="openCreate">新增关联</el-button></div>
    <div class="table-card"><el-table :data="links" v-loading="loading" empty-text="暂无任课关联记录">
      <el-table-column prop="class_name" label="班级" min-width="150" />
      <el-table-column prop="subject" label="所带学科" min-width="110" />
      <el-table-column prop="teacher_name" label="任课老师" min-width="140" />
      <el-table-column prop="teacher_username" label="教师账号" min-width="150" />
      <el-table-column label="操作" width="100"><template #default="{ row }"><el-button link type="danger" @click="remove(row)">解除关联</el-button></template></el-table-column>
    </el-table></div>
    <el-dialog v-model="visible" title="新增任课关联" width="460px"><el-form label-position="top">
      <el-form-item label="班级"><el-select v-model="form.class_id" filterable placeholder="选择班级" style="width:100%"><el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="任课老师"><el-select v-model="form.teacher_id" filterable placeholder="选择任课老师" style="width:100%"><el-option v-for="item in teachers" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="所带学科"><el-input v-model="form.subject" placeholder="例如：数学" clearable style="width:100%" /></el-form-item>
    </el-form><template #footer><el-button @click="visible=false">取消</el-button><el-button type="primary" @click="save">保存关联</el-button></template></el-dialog>
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createClassTeacherLink, deleteClassTeacherLink, listClassTeacherLinks } from '../../api/admin'
import { listClasses } from '../../api/classes'
import { listUsers } from '../../api/users'
const links = ref([]); const teachers = ref([]); const classes = ref([]); const loading = ref(false); const visible = ref(false)
const form = reactive({ class_id: null, teacher_id: null, subject: '' })
async function load() { loading.value = true; try { links.value = await listClassTeacherLinks() } finally { loading.value = false } }
async function openCreate() {
  Object.assign(form, { class_id: null, teacher_id: null, subject: '' })
  ;[teachers.value, classes.value] = await Promise.all([listUsers('subject_teacher'), listClasses()])
  visible.value = true
}
async function save() {
  if (!form.class_id || !form.teacher_id || !form.subject.trim()) return ElMessage.warning('请选择班级、任课老师并填写学科')
  await createClassTeacherLink({ class_id: form.class_id, teacher_id: form.teacher_id, subject: form.subject.trim() })
  ElMessage.success('任课关联已建立'); visible.value = false; load()
}
async function remove(row) { try { await ElMessageBox.confirm(`确认解除「${row.teacher_name}」在「${row.class_name}」的「${row.subject}」任课关联？`, '解除关联', { type: 'warning' }) } catch { return }; await deleteClassTeacherLink(row.id); ElMessage.success('关联已解除'); load() }
onMounted(load)
</script>
<style scoped>
.admin-subject-page{display:flex;flex-direction:column;gap:20px}.page-header{display:flex;justify-content:space-between;align-items:flex-start}.page-title{margin:0 0 4px;font-size:22px;color:var(--ink)}.header-desc{margin:0;color:#64748b;font-size:13.5px}.table-card{background:#fff;border:1px solid #e2e8f0;border-radius:var(--radius);padding:16px 18px}
</style>
