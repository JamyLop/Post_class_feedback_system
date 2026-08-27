<template>
  <div class="page">
    <div class="page-header"><div><span class="page-title">家长学生关联</span><p>建立关联后，家长只能查看该学生由班主任确认发布的一生一案。</p></div><el-button type="primary" @click="openCreate">新增关联</el-button></div>
    <el-table :data="links" v-loading="loading">
      <el-table-column prop="parent_name" label="家长" min-width="160" />
      <el-table-column prop="student_name" label="学生" min-width="160" />
      <el-table-column prop="relationship" label="关系" width="120"><template #default="{ row }">{{ relationshipLabel(row.relationship) }}</template></el-table-column>
      <el-table-column prop="created_at" label="关联时间" width="190" />
      <el-table-column label="操作" width="100"><template #default="{ row }"><el-button link type="danger" @click="remove(row)">解除</el-button></template></el-table-column>
    </el-table>
    <el-dialog v-model="visible" title="新增家长学生关联" width="460px">
      <el-form label-position="top">
        <el-form-item label="家长账号"><el-select v-model="form.parent_id" filterable placeholder="选择家长"><el-option v-for="item in parents" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="学生账号"><el-select v-model="form.student_id" filterable placeholder="选择学生"><el-option v-for="item in students" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="关系"><el-select v-model="form.relationship"><el-option label="父亲" value="father" /><el-option label="母亲" value="mother" /><el-option label="监护人" value="guardian" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="visible = false">取消</el-button><el-button type="primary" @click="save">保存关联</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createGuardianLink, deleteGuardianLink, listGuardianLinks } from '../../api/admin'
import { listUsers } from '../../api/users'

const links = ref([]); const parents = ref([]); const students = ref([]); const loading = ref(false); const visible = ref(false)
const form = reactive({ parent_id: null, student_id: null, relationship: 'guardian' })
const relationshipLabel = (value) => ({ father: '父亲', mother: '母亲', guardian: '监护人' }[value] || value)
async function load() { loading.value = true; try { links.value = await listGuardianLinks() } finally { loading.value = false } }
async function openCreate() { Object.assign(form, { parent_id: null, student_id: null, relationship: 'guardian' }); [parents.value, students.value] = await Promise.all([listUsers('parent'), listUsers('student')]); visible.value = true }
async function save() { if (!form.parent_id || !form.student_id) return ElMessage.warning('请选择家长和学生'); await createGuardianLink({ ...form }); ElMessage.success('关联已建立'); visible.value = false; load() }
async function remove(row) { try { await ElMessageBox.confirm(`确认解除「${row.parent_name}」与「${row.student_name}」的关联？`, '解除关联', { type: 'warning' }) } catch { return } await deleteGuardianLink(row.id); ElMessage.success('关联已解除'); load() }
onMounted(load)
</script>

<style scoped>
.page-header > div p { margin: 7px 0 0; color: #8492a6; font-size: 13px; }.el-select { width: 100%; }
</style>
