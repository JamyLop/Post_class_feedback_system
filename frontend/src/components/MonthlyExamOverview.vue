<template>
  <section class="exam-overview" aria-label="月考成绩总览">
    <div class="overview-filters">
      <label>考试月份<el-date-picker v-model="filters.exam_month" type="month" value-format="YYYY-MM" :clearable="false" @change="filters.grade = ''; filters.subject = ''; reload()" /></label>
      <label>年级<el-select v-model="filters.grade" clearable placeholder="全部年级" @change="filters.subject = ''; reload()"><el-option v-for="grade in result.grades" :key="grade" :label="grade" :value="grade" /></el-select></label>
      <label>班级<el-select v-model="filters.class_id" clearable placeholder="全部可见班级" @change="filters.subject = ''; reload()"><el-option v-for="cls in classes" :key="cls.id" :label="cls.name" :value="cls.id" /></el-select></label>
      <label>排序<el-select v-model="filters.subject" clearable :placeholder="showTotals ? '总分从高到低' : '默认顺序'" @change="reload"><el-option v-for="subject in result.subjects" :key="subject" :label="`${subject}从高到低`" :value="subject" /></el-select></label>
      <label>学生姓名<el-input v-model="filters.keyword" clearable placeholder="输入姓名后回车" @keyup.enter="reload" @clear="reload" /></label>
      <el-button :loading="loading" @click="reload">查询成绩</el-button>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-else>
      <div class="overview-caption">
        <strong>{{ result.exam_month || '暂无月份' }} · {{ result.total }} 名已录入学生</strong>
        <el-radio-group v-model="rankMode" size="small" aria-label="科目排名范围"><el-radio-button value="class_rank">班内排名</el-radio-button><el-radio-button value="scope_rank">可见范围排名</el-radio-button></el-radio-group>
      </div>
      <p class="ranking-note">{{ result.ranking_note }}</p>
      <p class="scroll-hint">左右滑动表格可查看全部科目及排名。</p>
      <el-table v-loading="loading" :data="result.items" empty-text="本月暂无可见成绩，请切换月份或联系班主任录入。" border>
        <el-table-column label="学生 / 班级" min-width="160" fixed>
          <template #default="{ row }"><strong>{{ row.student_name }}</strong><div class="secondary">{{ row.class_name }} · {{ row.grade }}</div></template>
        </el-table-column>
        <el-table-column v-if="showTotals" label="总分 / 满分" min-width="150">
          <template #default="{ row }">
            <template v-if="row.can_view_total"><strong>{{ row.total_score ?? '—' }} / {{ row.total_max_score ?? '—' }}</strong></template>
            <span v-else>仅可见任教学科</span>
          </template>
        </el-table-column>
        <el-table-column v-if="showTotals" label="总分班内排名" width="116"><template #default="{ row }">{{ row.class_rank ?? '—' }}</template></el-table-column>
        <el-table-column v-if="showTotals" label="总分范围排名" width="116"><template #default="{ row }">{{ row.scope_rank ?? '—' }}</template></el-table-column>
        <el-table-column v-for="subject in result.subjects" :key="subject" :label="subject" min-width="130">
          <template #default="{ row }"><template v-if="row.scores[subject]">{{ row.scores[subject].score }} / {{ row.scores[subject].max_score }}<div class="secondary">{{ rankMode === 'class_rank' ? '班内' : '范围' }}第 {{ row.scores[subject][rankMode] }} 名</div></template><span v-else>—</span></template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="50" :total="result.total" layout="prev, pager, next, total" @current-change="load" />
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getMonthlyExamOverview } from '../api/weeklyScores'

const props = defineProps({ classes: { type: Array, default: () => [] }, scope: { type: String, default: 'teaching' } })
const filters = ref({ exam_month: '', grade: '', class_id: null, subject: '', keyword: '' })
const result = ref({ items: [], subjects: [], grades: [], total: 0, ranking_note: '' })
const page = ref(1)
const rankMode = ref('class_rank')
const loading = ref(false)
const error = ref('')
const showTotals = computed(() => result.value.has_total_access)
let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  const params = Object.fromEntries(Object.entries(filters.value).filter(([, value]) => value !== '' && value != null))
  try {
    const data = await getMonthlyExamOverview({ ...params, scope: props.scope, limit: 50, offset: (page.value - 1) * 50 })
    if (id !== requestId) return
    result.value = data
    if (!filters.value.exam_month && data.exam_month) filters.value.exam_month = data.exam_month
  } catch (e) {
    if (id === requestId) error.value = e?.response?.data?.detail || '成绩加载失败，请点击查询成绩重试。'
  } finally { if (id === requestId) loading.value = false }
}
function reload() { page.value = 1; load() }
defineExpose({ load })
onMounted(load)
</script>

<style scoped>
.exam-overview { padding: 20px; background: #fff; border: 1px solid #e5eaf2; border-radius: 8px; min-width: 0; }
.overview-filters { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; margin-bottom: 20px; }
.overview-filters label { display: flex; flex-direction: column; gap: 6px; width: 170px; font-size: 13px; color: #445269; }
.overview-filters :deep(.el-select), .overview-filters :deep(.el-date-editor) { width: 100%; }
.overview-caption { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: center; }
.ranking-note, .secondary { color: #445269; font-size: 12px; line-height: 1.6; }
.ranking-note { margin: 12px 0 16px; max-width: 75ch; }
.scroll-hint { display: none; font-size: 12px; color: #445269; }
.el-pagination { margin-top: 20px; flex-wrap: wrap; }
@media (max-width: 900px) { .scroll-hint { display: block; } }
@media (max-width: 600px) { .exam-overview { padding: 12px; } .overview-filters label { width: calc(50% - 8px); min-width: 0; } }
</style>
