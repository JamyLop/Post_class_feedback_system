<template>
  <view class="writing-query">
    <view class="step-heading">
      <button v-if="selectedStudent" size="mini" @click="backToStudents">返回学生列表</button>
      <text class="step-title">{{ selectedStudent ? `${selectedStudent.student_name} · 科目填写状态` : '学生填写进度' }}</text>
      <text class="note">{{ selectedStudent ? '第二步：选择科目' : '第一步：选择学生' }}</text>
    </view>
    <view v-if="!selectedStudent" class="query-filters">
      <view class="field"><text>班级</text><picker :range="classNames" :value="classIndex" @change="changeClass"><view class="picker">{{ classNames[classIndex] }} ▾</view></picker></view>
      <view class="field"><text>月份</text><picker mode="date" fields="month" :value="month" @change="changeMonth"><view class="picker">{{ month }} ▾</view></picker></view>
      <view class="field"><text>填写状态</text><picker :range="statusNames" :value="statusIndex" @change="changeStatus"><view class="picker">{{ statusNames[statusIndex] }} ▾</view></picker></view>
    </view>
    <view v-if="!selectedStudent" class="search"><input v-model="keyword" placeholder="搜索学生" confirm-type="search" @confirm="query" /><button size="mini" :disabled="loading" @click="query">查询</button></view>
    <text class="note">{{ selectedStudent ? `${selectedStudent.class_name} · ${selectedStudent.month_label}，点击科目操作进入评定。` : scope === 'supervision' ? '查看本学段所有老师的填写进度；点击学生查看各科状态与评定内容。' : '科目与该生入学评定一致。班主任查看全部进度，任课老师查看本人科目。' }}</text>
    <view v-if="error" class="message"><text>填写状态加载失败</text><button size="mini" @click="load">重试</button></view>
    <template v-else>
      <text class="counts">{{ selectedStudent ? '' : `共 ${result.student_total} 名学生 · ` }}共 {{ result.total }} 项 · 已填写 {{ result.written }} 项 · 未填写 {{ result.unwritten }} 项</text>
      <text v-if="loading" class="message">加载中…</text>
      <text v-else-if="!(selectedStudent ? result.items : result.students)?.length" class="message">{{ selectedStudent ? '尚未建立入学评定科目，请先补充入学评定' : '当前条件下没有学生，请调整筛选条件' }}</text>
      <view v-else-if="!selectedStudent" class="results">
        <view v-for="student in result.students" :key="`${student.class_id}-${student.student_id}`" class="result-row" @click="selectStudent(student)">
          <view class="student-info">
            <view class="row-title"><text class="name">{{ student.student_name }}</text><text class="tag" :class="{ written: !student.unwritten && !student.initial_required }">{{ student.initial_required ? '待建立入学评定' : student.unwritten ? `${student.unwritten} 项未填写` : '全部已填写' }}</text></view>
            <text class="meta">{{ student.class_name }} · 已填 {{ student.written }} / {{ student.total }} 项</text>
          </view>
          <button size="mini" class="write-button" :disabled="loading" @click.stop="selectStudent(student)">查看科目</button>
        </view>
      </view>
      <view v-else class="results">
        <view v-for="row in result.items" :key="`${row.class_id}-${row.student_id}-${row.teacher_role}-${row.teacher_id}-${row.subject}`" class="result-row">
          <view class="student-info">
            <view class="row-title"><text class="name">{{ row.subject }}</text><text class="tag" :class="{ written: row.writing_status === 'written' }">{{ row.writing_status === 'written' ? '已填写' : '未填写' }}</text></view>
            <text class="meta">{{ row.assignment_required ? `${row.teacher_name} · 待关联账号` : `${row.teacher_name || (row.teacher_role === 'head_teacher' ? '班主任' : '任课老师')}填写${row.can_edit === false ? ' · 仅查看' : ''}` }}</text>
          </view>
          <button size="mini" class="write-button" :disabled="row.can_edit === false && row.writing_status !== 'written'" @click="openRow(row)">{{ row.assignment_required ? '待确认老师' : row.can_edit === false ? (row.writing_status === 'written' ? '查看评定' : '待老师填写') : (row.writing_status === 'written' ? '查看 / 修改' : '去填写') }}</button>
        </view>
      </view>
      <view v-if="pageTotal > 50" class="pagination"><button size="mini" :disabled="page === 1 || loading" @click="turnPage(-1)">上一页</button><text>{{ page }} / {{ Math.ceil(pageTotal / 50) }}</text><button size="mini" :disabled="page * 50 >= pageTotal || loading" @click="turnPage(1)">下一页</button></view>
    </template>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { listMonthlyWritingStatus } from '../api/monthlyReports'
const props = defineProps({ classes: { type: Array, default: () => [] }, scope: { type: String, default: 'teaching' } })
const classIndex = ref(0)
const classNames = computed(() => ['全部班级', ...props.classes.map(c => c.name)])
const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const statusNames = ['全部学生', '有已填写项', '有未填写项']
const statusValues = ['', 'written', 'unwritten']
const statusIndex = ref(0)
const keyword = ref('')
const page = ref(1)
const selectedStudent = ref(null)
const studentPage = ref(1)
const pageTotal = computed(() => selectedStudent.value ? result.value.filtered_total : result.value.student_total)
const loading = ref(false)
const error = ref(false)
const result = ref({ total: 0, written: 0, unwritten: 0, filtered_total: 0, items: [], students: [], student_total: 0 })
let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true
  error.value = false
  try {
    const params = { scope: props.scope, month_label: month.value, view: selectedStudent.value ? 'items' : 'students', limit: 50, offset: (page.value - 1) * 50 }
    // 微信 GET 会把 undefined 序列化为字符串，可选参数必须按需添加。
    if (selectedStudent.value) params.student_id = selectedStudent.value.student_id
    else params.keyword = keyword.value.trim()
    const cid = selectedStudent.value?.class_id || props.classes[classIndex.value - 1]?.id
    if (cid) params.class_id = cid
    if (!selectedStudent.value && statusValues[statusIndex.value]) params.writing_status = statusValues[statusIndex.value]
    const data = await listMonthlyWritingStatus(params)
    if (id === requestId) {
      result.value = data
      const lastPage = Math.max(1, Math.ceil(pageTotal.value / 50))
      if (page.value > lastPage) { page.value = lastPage; return load() }
    }
  } catch { if (id === requestId) error.value = true }
  finally { if (id === requestId) loading.value = false }
}
function query() { page.value = 1; load() }
function selectStudent(row) { studentPage.value = page.value; selectedStudent.value = row; page.value = 1; load() }
function backToStudents() { selectedStudent.value = null; page.value = studentPage.value; load() }
function changeClass(e) { classIndex.value = Number(e.detail.value); query() }
function changeMonth(e) { month.value = e.detail.value; query() }
function changeStatus(e) { statusIndex.value = Number(e.detail.value); query() }
function turnPage(delta) { page.value += delta; load() }
function openRow(row) {
  if (row.can_edit === false) {
    if (row.report_id && row.writing_status === 'written') uni.navigateTo({ url: `/subTeacher/monthlyReports/detail?id=${row.report_id}${props.scope === 'supervision' ? '&readonly=1' : ''}` })
    return
  }
  uni.navigateTo({ url: `/subTeacher/monthlyReports/generate?classId=${row.class_id}&studentId=${row.student_id}&month=${row.month_label}&evaluationRole=${row.teacher_role}` })
}
defineExpose({ load })
onMounted(load)
</script>

<style scoped>
.writing-query { background: #fff; border: 1rpx solid var(--mp-line); border-radius: 10rpx; padding: 24rpx; display: flex; flex-direction: column; gap: 20rpx; }
.step-heading { display: flex; flex-direction: column; align-items: flex-start; gap: 12rpx; }
.step-heading button { margin: 0; }
.step-title { font-size: 30rpx; font-weight: 600; color: var(--mp-ink); overflow-wrap: anywhere; }
.query-filters { display: flex; flex-wrap: wrap; gap: 16rpx; }
.field { flex: 1; min-width: 180rpx; font-size: 24rpx; color: var(--mp-body, #445269); }
.picker { margin-top: 8rpx; padding: 16rpx 12rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; color: var(--mp-ink); }
.search { display: flex; align-items: center; gap: 16rpx; }
.search input { min-width: 0; flex: 1; padding: 16rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; font-size: 26rpx; }
.search button { flex: none; margin: 0; }
.note, .meta { display: block; color: var(--mp-body, #445269); font-size: 24rpx; line-height: 1.6; }
.counts { color: var(--mp-ink); font-size: 26rpx; }
.message { display: block; text-align: center; padding: 24rpx 0; font-size: 26rpx; color: var(--mp-body, #445269); }
.result-row { display: flex; align-items: center; gap: 16rpx; padding: 22rpx 0; border-top: 1rpx solid var(--mp-line); }
.student-info { flex: 1; min-width: 0; }
.row-title { display: flex; flex-wrap: wrap; gap: 10rpx; align-items: center; margin-bottom: 8rpx; }
.name { font-size: 28rpx; font-weight: 600; color: var(--mp-ink); overflow-wrap: anywhere; }
.tag { flex: none; white-space: nowrap; font-size: 24rpx; color: #865c1e; background: #fbf1df; border-radius: 6rpx; padding: 4rpx 12rpx; }
.tag.written { color: #286349; background: #eaf3ee; }
.write-button { flex: none; width: 156rpx; margin: 0; padding: 0 12rpx; white-space: nowrap; font-size: 24rpx; color: var(--mp-primary); background: #fff; }
.pagination { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; font-size: 24rpx; }
.pagination button { margin: 0; }
</style>
