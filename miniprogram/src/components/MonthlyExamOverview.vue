<template>
  <view class="overview">
    <view class="exam-filters">
      <!-- 使用明确的两行布局，避免小程序对 flex-basis 中 calc 的兼容差异。 -->
      <view class="exam-filter-row">
        <view class="exam-filter-field"><text class="exam-filter-label">月份</text><picker class="exam-select" mode="date" fields="month" :value="month" @change="month = $event.detail.value; gradeIndex = 0; sortIndex = 0; reload()"><view class="exam-control"><text class="exam-control-value">{{ month || '最近一次月考' }}</text><text class="exam-control-arrow">▾</text></view></picker></view>
        <view class="exam-filter-field"><text class="exam-filter-label">班级</text><picker class="exam-select" :range="classNames" :value="classIndex" @change="classIndex = Number($event.detail.value); sortIndex = 0; reload()"><view class="exam-control"><text class="exam-control-value">{{ classNames[classIndex] }}</text><text class="exam-control-arrow">▾</text></view></picker></view>
      </view>
      <view class="exam-filter-row">
        <view class="exam-filter-field"><text class="exam-filter-label">年级</text><picker class="exam-select" :range="gradeNames" :value="gradeIndex" @change="gradeIndex = Number($event.detail.value); sortIndex = 0; reload()"><view class="exam-control"><text class="exam-control-value">{{ gradeNames[gradeIndex] || '全部年级' }}</text><text class="exam-control-arrow">▾</text></view></picker></view>
        <view class="exam-filter-field"><text class="exam-filter-label">排序</text><picker class="exam-select" :range="sortNames" :value="sortIndex" @change="sortIndex = Number($event.detail.value); reload()"><view class="exam-control"><text class="exam-control-value">{{ sortNames[sortIndex] || '选择科目' }}</text><text class="exam-control-arrow">▾</text></view></picker></view>
      </view>
    </view>
    <view class="exam-search"><input v-model="keyword" class="exam-search-input" placeholder="搜索学生姓名" confirm-type="search" @confirm="reload" /><button class="exam-query-button" :loading="loading" :disabled="loading" @click="reload">查询</button></view>
    <view v-if="error" class="error">{{ error }}</view>
    <template v-else>
      <view class="exam-caption"><text class="exam-count">已录入 {{ result.total }} 人</text><picker class="exam-rank-select" :range="rankNames" :value="rankIndex" @change="rankIndex = Number($event.detail.value)"><view class="exam-rank-control">{{ rankNames[rankIndex] }}<text class="exam-control-arrow">▾</text></view></picker></view>
      <view class="exam-rules-row"><text class="exam-rules-summary">科目与入学评定一致，同分并列</text><button class="exam-rules-toggle" :aria-expanded="rulesExpanded" @click="rulesExpanded = !rulesExpanded">{{ rulesExpanded ? '收起规则' : '排名规则' }}</button></view>
      <text v-if="rulesExpanded" class="exam-rules-detail">{{ result.ranking_note }}</text>
      <text v-if="result.items.length" class="exam-scroll-hint">左右滑动查看各科成绩及排名 ›</text>
      <text v-if="loading" class="note">正在读取成绩…</text>
      <text v-else-if="!result.items.length" class="note">本月暂无可见成绩，请切换月份或联系班主任录入。</text>
      <scroll-view v-else scroll-x class="table-scroll">
        <view class="table" :style="{ width: tableWidth + 'rpx' }">
          <view class="table-row table-head"><view class="name-cell">学生 / 班级</view><view v-if="result.has_total_access" class="total-cell">总分 / 满分</view><view v-if="result.has_total_access" class="rank-cell">总分排名</view><view v-for="subject in result.subjects" :key="subject" class="score-cell">{{ subject }}</view></view>
          <view v-for="row in result.items" :key="row.class_id + '-' + row.student_id" class="table-row">
            <view class="name-cell"><text class="name">{{ row.student_name }}</text><text class="secondary">{{ row.class_name }}</text></view>
            <view v-if="result.has_total_access" class="total-cell"><template v-if="row.can_view_total"><text>{{ row.total_score ?? '—' }} / {{ row.total_max_score ?? '—' }}</text></template><text v-else>仅任教学科</text></view>
            <view v-if="result.has_total_access" class="rank-cell">{{ row[rankField] || '—' }}</view>
            <view v-for="subject in result.subjects" :key="subject" class="score-cell"><template v-if="row.scores[subject]"><text>{{ row.scores[subject].score }} / {{ row.scores[subject].max_score }}</text><text class="secondary">第 {{ row.scores[subject][rankField] }} 名</text></template><text v-else>—</text></view>
          </view>
        </view>
      </scroll-view>
      <view class="pagination"><button :disabled="page <= 1 || loading" @click="page--; load()">上一页</button><text>{{ page }} / {{ Math.max(1, Math.ceil(result.total / 50)) }}</text><button :disabled="page * 50 >= result.total || loading" @click="page++; load()">下一页</button></view>
    </template>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getMonthlyExamOverview } from '../api/weeklyScores'
const props = defineProps({ classes: { type: Array, default: () => [] }, scope: { type: String, default: 'teaching' } })
const month = ref('')
const keyword = ref('')
const classIndex = ref(0)
const sortIndex = ref(0)
const gradeIndex = ref(0)
const rankIndex = ref(0)
const rulesExpanded = ref(false)
const rankNames = ['班内排名', '可见范围排名']
const rankField = computed(() => rankIndex.value ? 'scope_rank' : 'class_rank')
const page = ref(1)
const loading = ref(false)
const error = ref('')
const result = ref({ items: [], subjects: [], grades: [], total: 0, has_total_access: false })
const classNames = computed(() => ['全部可见班级', ...props.classes.map(cls => cls.name)])
const gradeNames = computed(() => ['全部年级', ...result.value.grades])
const sortNames = computed(() => [result.value.has_total_access ? '总分从高到低' : '默认顺序', ...result.value.subjects.map(name => name + '从高到低')])
const tableWidth = computed(() => 220 + (result.value.has_total_access ? 350 : 0) + result.value.subjects.length * 190)
let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  const params = { scope: props.scope, limit: 50, offset: (page.value - 1) * 50 }
  if (month.value) params.exam_month = month.value
  if (classIndex.value) params.class_id = props.classes[classIndex.value - 1]?.id
  if (gradeIndex.value) params.grade = result.value.grades[gradeIndex.value - 1]
  if (sortIndex.value) params.subject = result.value.subjects[sortIndex.value - 1]
  if (keyword.value.trim()) params.keyword = keyword.value.trim()
  try {
    const data = await getMonthlyExamOverview(params)
    if (id !== requestId) return
    result.value = data
    if (!month.value && data.exam_month) month.value = data.exam_month
  } catch (failure) {
    if (id !== requestId) return
    // 旧服务的动态路由可能返回405，明确提示版本未同步，避免误判为暂无成绩。
    const status = failure?.status
    error.value = [404, 405].includes(status) ? '成绩总览接口尚未部署，请更新后端服务后重试。'
      : status === 403 ? '当前账号无权查看成绩总览，请联系管理员核对角色。'
      : status === 401 ? '登录已过期，请重新登录。'
      : '成绩加载失败，请检查网络后点击查询重试。'
  }
  finally { if (id === requestId) loading.value = false }
}
function reload() { page.value = 1; load() }
defineExpose({ load })
onMounted(load)
</script>

<style scoped>
.overview { background: #fff; border: 1rpx solid var(--mp-line); border-radius: 8rpx; padding: 24rpx; min-width: 0; box-sizing: border-box; }
.exam-filters { width: 100%; }
.exam-filter-row { display: flex; flex-direction: row; align-items: flex-start; margin-bottom: 20rpx; }
.exam-filter-field { flex: 1; width: 0; min-width: 0; box-sizing: border-box; font-size: 24rpx; color: var(--mp-body, #37465b); }
.exam-filter-field + .exam-filter-field { margin-left: 20rpx; }
.exam-filter-label { display: block; margin-bottom: 8rpx; font-size: 24rpx; line-height: 1.5; }
.exam-select { display: block; width: 100%; min-width: 0; }
.exam-control { display: flex; flex-direction: row; align-items: center; justify-content: space-between; width: 100%; height: 80rpx; padding: 0 20rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; background: #f8fafc; box-sizing: border-box; }
.exam-control-value { flex: 1; min-width: 0; font-size: 26rpx; color: var(--mp-ink, #182337); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.exam-control-arrow { flex: none; margin-left: 10rpx; color: var(--mp-muted, #617086); font-size: 22rpx; }
.exam-search { display: flex; flex-direction: row; align-items: center; margin: 4rpx 0 24rpx; }
.exam-search-input { display: block; flex: 1; width: 0; min-width: 0; height: 80rpx; padding: 0 20rpx; border: 1rpx solid var(--mp-line); border-radius: 8rpx; background: #f8fafc; font-size: 26rpx; box-sizing: border-box; }
.exam-query-button { flex: none; display: flex; align-items: center; justify-content: center; width: 112rpx; height: 80rpx; margin: 0 0 0 16rpx; padding: 0; line-height: 1.5; font-size: 26rpx; color: #fff; background: var(--mp-primary, #253d61); border: 0; border-radius: 8rpx; }
.exam-query-button::after, .exam-rules-toggle::after { border: 0; }
button { margin: 0; font-size: 24rpx; color: #1762d4; background: #f4f7fb; border-radius: 8rpx; }
.exam-caption { display: flex; flex-direction: row; align-items: center; justify-content: space-between; min-height: 72rpx; padding-top: 16rpx; border-top: 1rpx solid var(--mp-line); font-size: 26rpx; }
.exam-count { flex: 1; min-width: 0; font-weight: 600; color: var(--mp-ink, #182337); }
.exam-rank-select { display: block; flex: none; margin-left: 16rpx; }
.exam-rank-control { display: flex; align-items: center; min-height: 64rpx; color: var(--mp-primary, #253d61); font-size: 24rpx; white-space: nowrap; }
.exam-rules-row { display: flex; flex-direction: row; align-items: center; justify-content: space-between; margin: 4rpx 0 12rpx; }
.exam-rules-summary { flex: 1; min-width: 0; font-size: 24rpx; color: var(--mp-body, #37465b); line-height: 1.6; }
.exam-rules-toggle { flex: none; margin: 0 0 0 12rpx; padding: 12rpx 0 12rpx 8rpx; font-size: 24rpx; line-height: 1.5; color: var(--mp-primary, #253d61); background: transparent; border: 0; white-space: nowrap; }
.exam-rules-detail { display: block; padding: 16rpx; margin-bottom: 16rpx; background: var(--mp-soft, #edf1f7); border-radius: 8rpx; font-size: 24rpx; color: var(--mp-body, #37465b); line-height: 1.7; }
.exam-scroll-hint { display: block; margin: 0 0 16rpx; color: var(--mp-muted, #617086); font-size: 24rpx; line-height: 1.6; }
.note { display: block; font-size: 24rpx; color: #445269; line-height: 1.7; margin: 16rpx 0; }
.table-scroll { width: 100%; }
.table { font-size: 26rpx; font-variant-numeric: tabular-nums; }
.table-row { display: flex; border-bottom: 1rpx solid var(--mp-line); align-items: stretch; }
.table-head { background: #f4f7fb; font-weight: 600; }
.name-cell, .total-cell, .rank-cell, .score-cell { flex-shrink: 0; padding: 18rpx 12rpx; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
.name-cell { width: 220rpx; } .total-cell { width: 230rpx; } .rank-cell { width: 120rpx; } .score-cell { width: 190rpx; }
.name { font-weight: 600; } .secondary { color: #445269; font-size: 24rpx; margin-top: 6rpx; }
.pagination { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; margin-top: 24rpx; font-size: 24rpx; }
.error { color: #b42318; font-size: 26rpx; padding: 20rpx 0; }
</style>
