// 仅使用合成数据拦截 API，验证真实 Vue 页面，不连接或修改学校数据。
import { createRequire } from 'node:module'
import fs from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.UI_BASE || 'http://127.0.0.1:5176'
const output = path.resolve(process.env.UI_OUTPUT || 'artifacts/ui-review')
await fs.mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const results = [], errors = []
const cases = [
  { id: 101, student_id: 21, student_name: '陈同学', class_id: 1, class_name: '高三（1）班', version: 2, status: 'revision_required', updated_at: '2026-09-05T08:30:00' },
  { id: 102, student_id: 22, student_name: '林同学', class_id: 2, class_name: '高三（2）班', version: 1, status: 'executing', updated_at: '2026-09-04T14:20:00' },
]
const report = { id: 1, student_id: 21, student_name: '陈同学', month_label: '2026-08', status: 'published', final_content: '本月学习节奏逐渐稳定。建议继续保持错题复盘习惯，着重巩固函数与解析几何。', published_at: '2026-09-01T08:00:00' }
function detail(role) { return { ...cases[0], viewer_role: role, can_manage: role === 'teacher', status: role === 'teacher' ? 'revision_required' : 'executing', overall_problem: '基础知识掌握较为扎实，但综合题中的条件分析与解题步骤仍需加强。\n本阶段重点提升限时训练的准确率，并建立每周复盘习惯。', admission_target: '稳步提升总分，明确目标院校与专业方向。', current_summary: '已完成第一轮学科诊断，正在落实本周强化任务。', subject_plans: [{ id: 1, subject: '数学', teacher_id: 3, problem_location: '解析几何综合题中，运算过程与条件分析衔接不够稳定。', cause_analysis: '缺少系统的错题归纳与定时训练。', struggle_goal: '提高基础题得分率', gaokao_requirement: '掌握核心概念与解题方法', reinforcement: '每天完成一组针对性训练，周末集中复盘。' }], tasks: [{ id: 301, title: '完成解析几何专项训练与错题复盘', subject: '数学', starts_on: '2026-09-01', due_on: '2026-09-07', status: 'in_progress' }], task_checkins: [], reviews: [], student_profile: null } }
async function session(role, width = 390, failed = false) {
  const context = await browser.newContext({ viewport: { width, height: 844 }, isMobile: true, deviceScaleFactor: 1, hasTouch: true })
  await context.addInitScript(role => { if (role) { localStorage.setItem('token', 'ui-preview-only'); localStorage.setItem('user', JSON.stringify({ id: 21, name: '陈老师', username: 'preview', role, status: 'active' })) } }, role)
  await context.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (!url.pathname.startsWith('/api/')) return route.continue()
    if (failed) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '预览网络错误' }), headers: { 'Access-Control-Allow-Origin': '*' } })
    let data = []
    const p = url.pathname.replace('/api', '')
    if (p === '/auth/login') data = { access_token: 'ui-preview-only', user: { id: 21, name: '陈同学', role: 'student' } }
    else if (p === '/auth/me') data = { id: 21, name: '陈同学', role, username: 'preview', status: 'active', gender: '男', grade: '高三' }
    else if (p === '/auth/me/children') data = [{ student_id: 21, student_name: '陈同学', class_name: '高三（1）班', latest_case_status: 'executing', latest_case_summary: '本周重点巩固数学基础，持续跟进英语阅读。', cycle_name: '2026 秋季' }]
    else if (p === '/student-cases/progress') data = { total: 18, overdue_tasks: 2, long_unreviewed: 1, draft: 3, revision_required: 2, executing: 10, pending_confirmation: 3 }
    else if (p === '/student-cases' || p === '/student-cases/children') data = cases.filter(c => (!url.searchParams.get('class_id') || c.class_id === Number(url.searchParams.get('class_id'))) && (!url.searchParams.get('status') || c.status === url.searchParams.get('status')))
    else if (/^\/student-cases\/(101|102|my-case)$/.test(p)) data = detail(role)
    else if (p === '/classes') data = [{ id: 1, name: '高三（1）班', grade: '高三' }, { id: 2, name: '高三（2）班', grade: '高三' }]
    else if (/^\/classes\/\d+\/students$/.test(p)) data = [{ id: 21, name: '陈同学', username: 'student-preview' }]
    else if (p.includes('monthly-reports')) data = p.endsWith('/1') ? report : [report]
    else if (p.includes('weekly-test-scores')) data = [{ id: 1, student_name: '陈同学', subject: '数学', exam_name: '第一周阶段检测', exam_date: '2026-09-02', score: 108, max_score: 150 }]
    else if (p === '/admin/stats') data = { user_count: 120, class_count: 4, teacher_count: 12, student_count: 60, parent_count: 45, case_count: 52 }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data), headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' } })
  })
  const page = await context.newPage()
  page.on('pageerror', e => errors.push(e.message))
  page.on('console', message => { if (message.type() === 'error' && /^(TypeError|ReferenceError|Error:)/.test(message.text())) errors.push(message.text()) })
  return { context, page }
}
async function capture(page, name) {
  await page.waitForTimeout(250)
  const overflow = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }))
  assert.ok(overflow.scroll <= overflow.width + 1, `${name}: horizontal overflow ${JSON.stringify(overflow)}`)
  await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true })
  results.push({ name, ...overflow })
  if (results.length % 5 === 0) console.log(`Verified ${results.length} views; latest: ${name}`)
}
try {
  for (const width of [320, 390, 430]) {
    const { context, page } = await session('', width)
    await page.goto(`${base}/#/pages/login/index`); await page.locator('.hero-title').waitFor()
    await capture(page, `login-${width}`)
    await page.locator('input').nth(0).fill('preview'); await page.locator('input').nth(1).fill('preview-only')
    await page.locator('.btn-primary').first().click(); await page.locator('.focus-title').waitFor()
    assert.equal(await page.locator('.focus-title').innerText(), '我的档案')
    await context.close()
  }
  for (const role of ['teacher', 'student', 'parent', 'admin', 'deyu_director', 'subject_teacher', 'consultant']) {
    const { context, page } = await session(role)
    await page.goto(`${base}/#/pages/index/index`); await page.locator('.focus-title').waitFor()
    assert.equal(await page.locator('.is-disabled').count(), 0)
    await capture(page, `home-${role}`)
    await context.close()
  }
  const { context, page } = await session('teacher')
  await page.goto(`${base}/#/subTeacher/todo/index`); await page.locator('.stat-num').first().waitFor(); await capture(page, 'teacher-todo')
  await page.getByText('快速打卡', { exact: true }).click(); await page.getByText('选择打卡档案', { exact: true }).waitFor(); await page.locator('.case-row').first().waitFor()
  await page.locator('.case-row').first().click(); await page.getByText('选择任务', { exact: true }).waitFor(); await capture(page, 'teacher-checkin')
  await page.goto(`${base}/#/subTeacher/caseList/index`); await page.locator('.case-row').first().waitFor(); await capture(page, 'teacher-cases')
  await page.locator('input').fill('林'); assert.equal(await page.locator('.case-row').count(), 1)
  await page.getByText('重置筛选', { exact: true }).click(); await page.waitForFunction(() => document.querySelectorAll('.case-row').length === 2)
  await page.locator('.case-row').first().click(); await page.locator('.section-body').first().waitFor(); await capture(page, 'teacher-case-detail')
  await page.getByText('学科', { exact: true }).click(); await page.locator('.plan-card').waitFor(); await capture(page, 'teacher-subject-plan')
  await page.getByText('编辑', { exact: true }).first().click(); await page.locator('textarea').first().waitFor(); await capture(page, 'teacher-case-edit')
  await context.close()
  for (const [role, route, ready, name] of [
    ['parent', '/subParent/children/index', '.child-card', 'parent-children'],
    ['parent', '/subParent/caseDetail/index?id=101', '.header-card', 'parent-case'],
    ['student', '/pages/student/myCase/index', '.header-card', 'student-case'],
    ['student', '/pages/student/monthlyReports/index', '.report-card', 'student-monthly'],
    ['admin', '/subTeacher/adminStats/index', '.stat-card', 'admin-stats'],
    ['subject_teacher', '/subTeacher/caseList/index', '.case-row', 'subject-teacher-cases'],
    ['teacher', '/subTeacher/weeklyScores/index', '.score-list', 'weekly-scores'],
  ]) {
    const { context, page } = await session(role, 320)
    await page.goto(`${base}/#${route}`); await page.locator(ready).first().waitFor(); await capture(page, name)
    await context.close()
  }
  for (const [role, route] of [['parent', '/subParent/children/index'], ['teacher', '/subTeacher/todo/index'], ['teacher', '/subTeacher/caseList/index']]) {
    const { context, page } = await session(role, 390, true)
    await page.goto(`${base}/#${route}`); await page.getByText('加载未完成', { exact: true }).waitFor(); await capture(page, `${role}-${route.split('/')[2]}-error`)
    await context.close()
  }
  assert.deepEqual(errors, [], 'No uncaught runtime errors')
  await fs.writeFile(path.join(output, 'results.json'), JSON.stringify({ mockedApi: true, results, errors }, null, 2))
  console.log(`PASS ${results.length} viewport captures; login, navigation, search, reset, role isolation and error states verified. API responses are synthetic.`)
} finally { await browser.close() }
