import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import { ref, computed } from 'vue'
import { monthlySubjects } from '../src/utils/parentMonthlyReports.js'

const report = { id: 5, status: 'generated', final_content: '', evaluations: [
  { id: 2, teacher_role: 'subject_teacher', subject: '语文、历史', teacher_name: '演示老师', content: '原始评定内容' },
] }

test('管理员可查待发布内容及未填写德育；家长仍只看到已发布且有内容的科目', () => {
  const subjects = monthlySubjects([report], { publishedOnly: false, includeEmpty: true })
  assert.deepEqual(subjects.map(item => item.subject), ['德育', '语文', '历史'])
  assert.equal(subjects[1].entries[0].content, '原始评定内容')
  assert.deepEqual(monthlySubjects([report]), [])
  assert.deepEqual(monthlySubjects([{ ...report, status: 'published' }]).map(item => item.subject), ['语文', '历史'])
})

function mount(role = 'admin', loggedIn = true) {
  let onLoadHook, onShowHook
  const calls = { reads: [], redirects: [] }
  const api = { get: async () => report }
  const sandbox = {
    ref, computed, monthlySubjects,
    onLoad: callback => { onLoadHook = callback },
    onShow: callback => { onShowHook = callback },
    useAuthStore: () => ({ isLoggedIn: loggedIn, role }),
    getMonthlyReport: async id => { calls.reads.push(id); return api.get() },
    uni: { reLaunch: ({ url }) => calls.redirects.push(url) },
  }
  const source = fs.readFileSync(new URL('../src/subTeacher/monthlyReports/useAdminMonthlyReport.js', import.meta.url), 'utf8')
    .replace(/^import .*$/mg, '').replace('export function', 'function')
  vm.runInNewContext(`${source}\nglobalThis.view = useAdminMonthlyReport()`, sandbox)
  return { view: sandbox.view, api, calls, onLoad: options => onLoadHook(options), onShow: () => onShowHook() }
}

for (const subject of ['语文', encodeURIComponent('语文')]) test(`管理员详情兼容中文和编码参数：${subject}`, async () => {
  const page = mount()
  page.onLoad({ id: '5', subject, readonly: '1' })
  await page.onShow()
  assert.equal(page.view.subject.value, '语文')
  assert.equal(page.view.readOnly.value, true)
  assert.equal(page.view.subjects.value.find(item => item.subject === page.view.subject.value).entries[0].content, '原始评定内容')
  assert.deepEqual(page.calls.reads, [5])
  page.api.get = async () => { throw new Error('已移除或无权查看') }
  await page.onShow()
  assert.equal(page.view.report.value, null)
  assert.equal(page.view.error.value, '已移除或无权查看')
})

test('非管理员和访客不能从管理员阅读页发起业务读取', async () => {
  for (const [role, loggedIn, destination] of [['parent', true, '/pages/index/index'], ['teacher', true, '/pages/index/index'], ['admin', false, '/pages/login/index']]) {
    const page = mount(role, loggedIn)
    page.onLoad({ id: '5' })
    await page.onShow()
    assert.deepEqual(page.calls.reads, [])
    assert.deepEqual(page.calls.redirects, [destination])
  }
})

test('无效报告参数不发出读取请求，返回清晰的重试提示', async () => {
  const page = mount()
  page.onLoad({ id: 'bad', subject: '%E8%AF' })
  await page.onShow()
  assert.deepEqual(page.calls.reads, [])
  assert.match(page.view.error.value, /页面参数有误/)
})
