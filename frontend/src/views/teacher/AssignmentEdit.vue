<template>
  <div class="page">
    <div class="page-header">
      <span class="page-title">新建作业</span>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    <el-card style="max-width: 640px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="作业标题" />
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="form.subject" style="width: 100%">
            <el-option label="数学" value="数学" />
            <el-option label="语文" value="语文" />
            <el-option label="英语" value="英语" />
            <el-option label="物理" value="物理" />
            <el-option label="化学" value="化学" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="form.class_id" placeholder="选择班级" style="width: 100%">
            <el-option v-for="c in classes" :key="c.id" :label="`${c.name}（${c.grade}）`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker v-model="form.due_at" type="datetime" placeholder="可留空" style="width: 100%" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onCreate">创建作业</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createAssignment } from '../../api/assignments'
import { listClasses } from '../../api/classes'

const router = useRouter()
const classes = ref([])
const loading = ref(false)
const form = reactive({ title: '', subject: '数学', class_id: null, description: '', due_at: null })

async function onCreate() {
  if (!form.title || !form.class_id) {
    ElMessage.warning('请填写标题并选择班级')
    return
  }
  loading.value = true
  try {
    const a = await createAssignment({ ...form })
    ElMessage.success('创建成功，请添加题目')
    router.push(`/teacher/assignments/${a.id}`)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  classes.value = await listClasses()
})
</script>
