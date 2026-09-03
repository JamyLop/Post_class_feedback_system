<template>
  <div class="page admin-guardian-page">
    <div class="page-header"><div><h1 class="page-title">咨询老师与学生关联</h1><p class="header-desc">为咨询老师分配负责学生，教师端只展示其负责范围内的学生方案。</p></div><el-button type="primary" @click="openCreate">新增关联</el-button></div>
    <div class="table-card"><el-table :data="links" v-loading="loading" empty-text="暂无咨询老师关联记录">
      <el-table-column prop="consultant_name" label="咨询老师" min-width="150" />
      <el-table-column prop="consultant_username" label="教师账号" min-width="150" />
      <el-table-column prop="student_name" label="学生" min-width="140" />
      <el-table-column prop="student_username" label="学号" min-width="170" />
      <el-table-column label="操作" width="100"><template #default="{ row }"><el-button link type="danger" @click="remove(row)">解除关联</el-button></template></el-table-column>
    </el-table></div>
    <el-dialog v-model="visible" title="新增咨询老师关联" width="460px"><el-form label-position="top">
      <el-form-item label="咨询老师"><el-select v-model="form.consultant_id" filterable placeholder="选择教师" style="width:100%"><el-option v-for="item in teachers" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" /></el-select></el-form-item>
      <el-form-item label="学生"><el-select v-model="form.student_id" filterable placeholder="选择学生" style="width:100%"><el-option v-for="item in students" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" /></el-select></el-form-item>
    </el-form><template #footer><el-button @click="visible=false">取消</el-button><el-button type="primary" @click="save">保存关联</el-button></template></el-dialog>
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createConsultantLink, deleteConsultantLink, listConsultantLinks } from '../../api/admin'
import { listUsers } from '../../api/users'
const links = ref([]); const teachers = ref([]); const students = ref([]); const loading = ref(false); const visible = ref(false)
const form = reactive({ consultant_id: null, student_id: null })
async function load() { loading.value = true; try { links.value = await listConsultantLinks() } finally { loading.value = false } }
async function openCreate() { Object.assign(form, { consultant_id: null, student_id: null }); [teachers.value, students.value] = await Promise.all([listUsers('teacher'), listUsers('student')]); visible.value = true }
async function save() { if (!form.consultant_id || !form.student_id) return ElMessage.warning('请选择咨询老师和学生'); await createConsultantLink({ ...form }); ElMessage.success('咨询老师关联已建立'); visible.value = false; load() }
async function remove(row) { try { await ElMessageBox.confirm(`确认解除「${row.consultant_name}」与「${row.student_name}」的关联？`, '解除关联', { type: 'warning' }) } catch { return }; await deleteConsultantLink(row.id); ElMessage.success('关联已解除'); load() }
onMounted(load)
</script>
<style scoped>
.admin-guardian-page{display:flex;flex-direction:column;gap:20px}.page-header{display:flex;justify-content:space-between;align-items:flex-start}.page-title{margin:0 0 4px;font-size:22px;color:var(--ink)}.header-desc{margin:0;color:#64748b;font-size:13.5px}.table-card{background:#fff;border:1px solid #e2e8f0;border-radius:var(--radius);padding:16px 18px}
</style>
