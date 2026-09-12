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
let savedManual = null
const mutations = []
async function mockMonthly(page) {
 await page.route('**/api/monthly-reports**', async route => {
  const req = route.request(), p = new URL(req.url()).pathname, method = req.method()
  if (method === 'OPTIONS') return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS'}})
  assert.ok(!p.endsWith('/generate'), 'No AI generation requests')
  if (method === 'POST' && p.endsWith('/monthly-reports')) {
   savedManual = {...req.postDataJSON(),id:91,student_name:'陈同学',class_name:'高三（1）班',status:'generated',updated_at:'2026-09-05T08:00:00'}
   mutations.push('create')
  } else if (method === 'PUT') { Object.assign(savedManual,req.postDataJSON()); mutations.push('update') }
  else if (method === 'POST' && p.endsWith('/publish')) { savedManual.status='published'; mutations.push('publish') }
  const data = method === 'GET' && p.endsWith('/monthly-reports') ? (savedManual ? [savedManual] : []) : savedManual
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data),headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'}})
 })
}
try {
 const {context,page} = await session('teacher',390)
 await mockMonthly(page)
 await page.goto(`${base}/#/subTeacher/monthlyReports/generate?classId=1`)
 await page.locator('.picker-text').first().getByText('陈同学',{exact:true}).waitFor()
 await page.locator('.btn-submit').click()
 assert.equal(mutations.length,0)
 await page.locator('textarea').fill('本月学习积极，课堂表现有进步。下月坚持错题复盘。')
 await capture(page,'monthly-manual-create')
 await page.locator('.btn-submit').click()
 await page.locator('.content-text').waitFor()
 assert.equal(savedManual.final_content,'本月学习积极，课堂表现有进步。下月坚持错题复盘。')
 await page.getByText('编辑',{exact:true}).click()
 await page.locator('textarea').fill('教师手动修改后的月度评定')
 assert.equal(await page.getByText('发布',{exact:true}).count(),0)
 await page.getByText('保存',{exact:true}).click()
 await page.locator('.content-text').waitFor()
 await page.getByText('发布',{exact:true}).click()
 await page.locator('.uni-modal__btn_primary').click()
 await page.getByText('已发布',{exact:true}).waitFor()
 assert.deepEqual(mutations,['create','update','publish'])
 assert.equal(savedManual.final_content,'教师手动修改后的月度评定')
 await capture(page,'monthly-manual-published')
 await context.close()
 const web = await session('teacher',1280)
 await mockMonthly(web.page)
 await web.page.goto('http://127.0.0.1:5174/teacher/monthly-reports')
 await web.page.getByRole('button',{name:'新建月度评定'}).click()
 await web.page.locator('.el-dialog').filter({hasText:'填写月度评定'}).locator('.el-select').nth(1).click()
 await web.page.locator('.el-select-dropdown__item').filter({hasText:'陈同学'}).last().click()
 await web.page.locator('.el-dialog textarea').fill('网页端手写评定')
 await capture(web.page,'monthly-web-manual')
 await web.page.getByRole('button',{name:'保存待发布'}).click()
 await web.page.locator('.el-overlay-dialog').filter({visible:true}).waitFor({state:'hidden'})
 assert.equal(savedManual.final_content,'网页端手写评定')
 await web.page.getByRole('button',{name:'查看/编辑'}).first().click()
 await web.page.locator('.el-dialog textarea').fill('网页发布前的最新修改')
 await web.page.locator('.el-dialog').getByRole('button',{name:'发布',exact:true}).click()
 await web.page.locator('.el-dialog').getByText('已发布',{exact:true}).waitFor()
 assert.equal(savedManual.final_content,'网页发布前的最新修改')
 assert.deepEqual(errors,[])
 console.log('PASS: mini/web manual create, edit, publish; no AI calls; latest edits preserved')
 await web.context.close()
} finally { await browser.close() }
