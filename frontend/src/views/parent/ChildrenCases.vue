<template>
  <section class="archive-page">
    <header class="page-intro">
      <div class="intro-content">
        <div class="intro-copy">
          <p class="section-label">易飞特菁英全日制</p>
          <h1>孩子的一生一案</h1>
          <p class="intro-description">
            查阅由班主任与学科教师共同维护的学业发展方案、阶段记录与复盘结果。
          </p>
          <div class="intro-points" aria-label="档案特点">
            <span>目标清晰</span>
            <span>过程可查</span>
            <span>阶段复盘</span>
          </div>
        </div>

        <div class="intro-aside" aria-label="档案说明">
          <strong>{{ cases.length || 0 }}</strong>
          <span class="count-copy"><b>份学生档案</b><small>当前账号可查阅</small></span>
        </div>
      </div>

      <figure class="campus-figure">
        <div class="campus-photo">
          <img :src="campusImage" alt="易飞特菁英全日制学校综合楼" />
        </div>
        <figcaption>
          <span>易飞特菁英全日制</span>
          <strong>让优秀成为习惯</strong>
        </figcaption>
      </figure>
    </header>

    <section class="collaboration-strip" aria-label="家校协同流程">
      <div class="strip-title">
        <strong>家校协同</strong>
        <span>围绕学生成长持续记录</span>
      </div>
      <div class="strip-items">
        <div><i>建</i><span><strong>班主任主建</strong><small>建立学生发展总案</small></span></div>
        <div><i>研</i><span><strong>学科协同</strong><small>制定学科提升方案</small></span></div>
        <div><i>记</i><span><strong>过程留痕</strong><small>记录任务执行进展</small></span></div>
        <div><i>复</i><span><strong>阶段复盘</strong><small>根据结果动态调整</small></span></div>
      </div>
    </section>

    <div class="section-heading">
      <div>
        <h2>学生档案</h2>
        <p>仅显示已向家庭开放查阅的内容</p>
      </div>
      <span class="directory-count"><strong>{{ cases.length || 0 }}</strong> 份已开放</span>
    </div>

    <div v-if="loading" class="loading-list" aria-label="档案加载中">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="cases.length" class="archive-list">
      <router-link
        v-for="(item, index) in cases"
        :key="item.id"
        :to="`/parent/children/${item.id}`"
        class="archive-row"
      >
        <span class="row-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="student-monogram" aria-hidden="true">
          {{ item.student_name?.slice(0, 1) || '孩' }}
        </span>

        <span class="archive-copy">
          <span class="title-line">
            <strong>{{ item.student_name }}</strong>
            <span class="class-name">{{ item.class_name }}</span>
            <span class="status" :class="`is-${item.status}`">
              <i aria-hidden="true"></i>{{ statusLabel(item.status) }}
            </span>
          </span>
          <span class="summary">
            {{ item.current_summary || '班主任正在持续记录学业发展情况，当前档案可供查阅。' }}
          </span>
          <span class="archive-meta">第 {{ item.version }} 版 · 班主任建档 · 家长只读</span>
        </span>

        <span class="open-action">
          <span>查阅档案</span>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true">
            <path d="M5 12h13M14 7l5 5-5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </span>
      </router-link>
    </div>

    <div v-else class="empty-state">
      <span class="empty-symbol" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none">
          <path d="M6.5 3.5h8l3 3V20a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" stroke="currentColor" stroke-width="1.5" />
          <path d="M14.5 3.5v3h3M8.5 11h6M8.5 14.5h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        </svg>
      </span>
      <h3>暂无可查阅档案</h3>
      <p>班主任发布后，学生档案会自动显示在这里。</p>
    </div>

    <aside v-if="cases.length" class="privacy-note">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
        <path d="M12 21s7-3.5 7-9V5.5L12 3 5 5.5V12c0 5.5 7 9 7 9Z" stroke="currentColor" stroke-width="1.5" />
        <path d="m9.5 12 1.7 1.7 3.6-3.9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span>家长端仅提供只读查阅。如需调整内容，请联系班主任。</span>
    </aside>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getFamilyCases } from '../../api/studentCases'
import campusImage from '../../assets/yifeite-campus.jpg'

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
.archive-page {
  --ink: #20221f;
  --muted: #666b64;
  --faint: #898d86;
  --line: #d8d9d5;
  --brand-blue: #123f83;
  --brand-orange: #f28a18;
  --accent: var(--brand-blue);
  width: min(1160px, calc(100% - 48px));
  margin: 0 auto;
  padding: 46px 0 56px;
  color: var(--ink);
}

.page-intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  align-items: stretch;
  overflow: hidden;
  margin-bottom: 18px;
  border: 1px solid #d9dee5;
  border-top: 4px solid var(--brand-blue);
  background: #fff;
}

.intro-content {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  padding: 38px 42px 34px;
}

.intro-copy { max-width: 690px; }

.section-label {
  margin: 0 0 20px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.12em;
}

.section-label::before {
  content: '';
  display: inline-block;
  width: 22px;
  height: 2px;
  margin: 0 10px 3px 0;
  background: var(--brand-orange);
}

.page-intro h1 {
  margin: 0;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  font-size: 44px;
  font-weight: 650;
  line-height: 1.2;
  letter-spacing: 0.04em;
  text-wrap: balance;
}

.intro-description {
  max-width: 58ch;
  margin: 22px 0 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.8;
  text-wrap: pretty;
}

.intro-points {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
}

.intro-points span {
  padding: 6px 11px;
  border: 1px solid #d8e0eb;
  border-radius: 999px;
  background: #f4f7fb;
  color: #355273;
  font-size: 12px;
}

.intro-aside {
  display: flex;
  align-items: baseline;
  gap: 8px;
  width: max-content;
  padding-top: 18px;
  border-top: 2px solid var(--brand-orange);
}

.intro-aside strong {
  font-family: Georgia, "Times New Roman", serif;
  color: var(--brand-blue);
  font-size: 26px;
  font-weight: 500;
  line-height: 1;
}

.count-copy {
  display: grid;
  gap: 2px;
  color: var(--muted);
  font-size: 12px;
}

.count-copy b { color: #3f454d; font-weight: 600; }
.count-copy small { color: var(--faint); font-size: 11px; }

.campus-figure {
  overflow: hidden;
  margin: 0;
  border-radius: 2px;
  background: var(--brand-blue);
  border-left: 1px solid #d9dee5;
}

.campus-photo {
  overflow: hidden;
  height: 224px;
  background: #dbe4f0;
}

.campus-photo img {
  display: block;
  width: 180%;
  max-width: none;
  height: 100%;
  object-fit: cover;
  object-position: left center;
}

.campus-figure figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 72px;
  padding: 14px 20px;
  color: #fff;
}

.campus-figure figcaption span {
  font-size: 12px;
}

.campus-figure figcaption strong {
  color: #ffd49f;
  font-size: 12px;
  font-weight: 500;
}

.collaboration-strip {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  margin-bottom: 30px;
  background: var(--brand-blue);
  color: #fff;
}

.strip-title {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  padding: 22px 24px;
  border-right: 1px solid rgba(255, 255, 255, 0.22);
}

.strip-title strong { font-size: 16px; letter-spacing: 0.08em; }
.strip-title span { color: #c9d6e8; font-size: 11px; }

.strip-items {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.strip-items > div {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 18px 17px;
  border-right: 1px solid rgba(255, 255, 255, 0.16);
}

.strip-items > div:last-child { border-right: 0; }

.strip-items i {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  border: 1px solid rgba(255, 255, 255, 0.48);
  border-radius: 50%;
  color: #ffd49f;
  font-size: 12px;
  font-style: normal;
}

.strip-items span { display: grid; gap: 3px; min-width: 0; }
.strip-items strong { font-size: 13px; font-weight: 600; }
.strip-items small { overflow: hidden; color: #c9d6e8; font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 24px;
  border: 1px solid #d9dee5;
  border-bottom-color: var(--line);
  background: #fff;
}

.section-heading > div { display: grid; gap: 5px; }
.section-heading h2 { margin: 0; font-size: 17px; font-weight: 700; letter-spacing: 0.04em; }
.section-heading p { margin: 0; color: var(--muted); font-size: 12px; }
.directory-count { color: var(--muted); font-size: 12px; }
.directory-count strong { color: var(--brand-blue); font-family: Georgia, serif; font-size: 20px; font-weight: 500; }
.archive-list { border: 1px solid #d9dee5; border-top: 0; background: #fff; }

.archive-row {
  display: grid;
  grid-template-columns: 36px 54px minmax(0, 1fr) auto;
  align-items: center;
  gap: 22px;
  min-height: 142px;
  padding: 26px 24px;
  border-bottom: 1px solid var(--line);
  color: inherit;
  text-decoration: none;
  transition: background-color 180ms ease, padding 180ms ease;
}

.archive-row:last-child { border-bottom: 0; }

.archive-row:hover {
  background: #f2f5f8;
}

.archive-row:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

.row-index {
  align-self: start;
  padding-top: 5px;
  color: var(--faint);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 12px;
}

.student-monogram {
  display: grid;
  place-items: center;
  width: 50px;
  height: 50px;
  border: 1px solid #b9bbb6;
  color: var(--ink);
  font-family: "STSong", "SimSun", serif;
  font-size: 22px;
}

.archive-copy { display: grid; gap: 9px; min-width: 0; }

.title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px 12px;
}

.title-line strong { font-size: 18px; font-weight: 700; letter-spacing: 0.03em; }
.class-name { color: var(--muted); font-size: 13px; }

.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #506155;
  font-size: 12px;
}

.status i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status.is-pending_review, .status.is-pending_confirmation { color: #89672c; }
.status.is-revision_required { color: #9a4035; }
.status.is-adjusted { color: #5c6078; }
.status.is-archived, .status.is-draft { color: #747871; }

.summary {
  display: -webkit-box;
  overflow: hidden;
  color: #4f534e;
  font-size: 14px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.archive-meta { color: var(--faint); font-size: 12px; }

.open-action {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 112px;
  padding-bottom: 5px;
  border-bottom: 1px solid #94978f;
  color: var(--ink);
  font-size: 13px;
  font-weight: 650;
  transition: color 180ms ease, border-color 180ms ease;
}

.archive-row:hover .open-action { color: var(--accent); border-color: var(--accent); }
.archive-row:hover .open-action svg { transform: translateX(3px); }
.open-action svg { transition: transform 180ms ease; }

.loading-list { padding: 34px 24px; border: 1px solid #d9dee5; border-top: 0; background: #fff; }

.empty-state {
  display: grid;
  justify-items: center;
  padding: 72px 24px;
  border-bottom: 1px solid var(--line);
  text-align: center;
}

.empty-symbol {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  margin-bottom: 20px;
  border: 1px solid #b9bbb6;
  color: var(--muted);
}

.empty-state h3 { margin: 0 0 10px; font-size: 16px; }
.empty-state p { margin: 0; color: var(--muted); font-size: 13px; }

.privacy-note {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
  padding: 13px 16px;
  background: #eaf0f7;
  color: #5a6878;
  font-size: 12px;
}

@media (max-width: 760px) {
  .archive-page { width: calc(100% - 36px); padding-top: 42px; }
  .page-intro { grid-template-columns: 1fr; }
  .intro-content { padding: 30px 24px; }
  .page-intro h1 { font-size: 36px; }
  .intro-aside { margin-top: 30px; }
  .campus-figure { border-top: 1px solid #d9dee5; border-left: 0; }
  .campus-photo { height: 176px; }
  .collaboration-strip { grid-template-columns: 1fr; }
  .strip-title { border-right: 0; border-bottom: 1px solid rgba(255, 255, 255, 0.22); }
  .strip-items { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .strip-items > div:nth-child(2) { border-right: 0; }
  .strip-items > div:nth-child(-n + 2) { border-bottom: 1px solid rgba(255, 255, 255, 0.16); }
  .archive-row { grid-template-columns: 42px minmax(0, 1fr); gap: 16px; padding: 22px 0; }
  .row-index { display: none; }
  .student-monogram { width: 40px; height: 40px; font-size: 18px; }
  .open-action { grid-column: 2; width: max-content; min-width: 104px; }
  .archive-row { padding-right: 18px; padding-left: 18px; }
}

@media (max-width: 520px) {
  .campus-figure figcaption { align-items: flex-start; flex-direction: column; gap: 3px; }
  .section-heading p { display: none; }
  .privacy-note { align-items: flex-start; justify-content: flex-start; line-height: 1.6; }
}

@media (prefers-reduced-motion: reduce) {
  .archive-row, .open-action, .open-action svg { transition: none; }
}
</style>
