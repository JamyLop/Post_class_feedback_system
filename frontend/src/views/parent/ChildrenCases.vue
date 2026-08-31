<template>
  <section class="family-page">
    <header class="family-head">
      <div class="scope-badges">
        <span class="badge-tag">家校共育</span>
        <span class="badge-sub">学业发展档案</span>
      </div>
      <h1>孩子的一生一案</h1>
      <p>集中查阅班主任与各科任课教师共同制定的备考目标、学科攻坚方案与阶段复盘记录。</p>
    </header>

    <el-skeleton v-if="loading" :rows="4" animated />

    <div v-else-if="cases.length" class="case-list">
      <article
        v-for="item in cases"
        :key="item.id"
        class="case-card"
        @click="$router.push(`/parent/children/${item.id}`)"
      >
        <div class="student-mark">
          {{ item.student_name?.slice(0, 1) || '孩' }}
        </div>
        <div class="case-copy">
          <div class="title-row">
            <h2>{{ item.student_name }}</h2>
            <span class="class-label">{{ item.class_name }}</span>
            <span class="version-label">第 {{ item.version }} 版</span>
            <span class="badge-status" :class="`is-${item.status}`">
              {{ statusLabel(item.status) }}
            </span>
          </div>
          <p class="summary-text">{{ item.current_summary || '班主任正在持续记录学业发展情况。' }}</p>
        </div>
        <div class="card-action">
          <el-button type="primary" plain>查阅档案详情</el-button>
        </div>
      </article>
    </div>

    <el-empty v-else description="班主任尚未发布可查看的学生档案" :image-size="90" />
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getFamilyCases } from '../../api/studentCases'

const cases = ref([])
const loading = ref(false)

const statusLabel = (status) => ({
  draft: '草稿',
  pending_confirmation: '待德育审查',
  revision_required: '待班主任整改',
  executing: '执行中',
  pending_review: '待复盘',
  adjusted: '已调整',
  archived: '已归档',
}[status] || status)

async function load() {
  loading.value = true
  try {
    cases.value = await getFamilyCases()
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.family-page {
  width: min(1080px, calc(100% - 48px));
  margin: 0 auto;
  padding: 36px 0 64px;
}

.family-head {
  margin-bottom: 28px;
}

.scope-badges {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.badge-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 6px;
}

.badge-sub {
  font-size: 11px;
  color: #64748b;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 6px;
}

.family-head h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.family-head p {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
  line-height: 1.6;
}

.case-list {
  display: grid;
  gap: 14px;
}

.case-card {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius);
  box-shadow: none;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.case-card:hover {
  border-color: #cbd5e1;
  box-shadow: none;
}

.student-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  color: #2f5bff;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 18px;
  font-weight: 700;
}

.case-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-row h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--ink);
}

.class-label {
  color: #64748b;
  font-size: 13px;
}

.version-label {
  font-size: 11.5px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 6px;
  font-family: monospace;
}

.summary-text {
  margin: 0;
  color: #475569;
  font-size: 13.5px;
  line-height: 1.5;
}

@media (max-width: 680px) {
  .case-card {
    grid-template-columns: 42px 1fr;
  }
  .case-card .card-action {
    grid-column: 1 / -1;
  }
  .student-mark {
    width: 42px;
    height: 42px;
    font-size: 16px;
  }
}
</style>
