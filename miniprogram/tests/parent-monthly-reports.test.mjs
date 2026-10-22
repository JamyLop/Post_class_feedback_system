import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import { ref } from 'vue'
import { monthlyGroups, monthlySubjects, reviewSections } from '../src/utils/parentMonthlyReports.js'
import { formatReview } from '../src/utils/monthlyReview.js'

const report = {
  id: 1, status: 'published', month_label: '2026-09', final_content: '德育正文',
  evaluations: [
    { id: 1, teacher_role: 'head_teacher', teacher_name: '班主任', content: '德育正文' },
    { id: 2, teacher_role: 'subject_teacher', subject: '数学、物理', teacher_name: '任课老师', content: '联合评定' },
    { id: 3, teacher_role: 'subject_teacher', subject: '英语', content: '  ' },
  ],
}

for (const [platform, subjectParam] of [
  ['微信小程序', encodeURIComponent('语文')],
  ['H5', '语文'],
]) {
  test(`${platform}科目参数进入真实加载流程后能匹配中文科目和正文`, async () => {
    let onLoadHook, onShowHook
    const chineseReport = { ...report, evaluations: [{ id: 8, teacher_role: 'subject_teacher', subject: '语文', content: '语文评定正文' }] }
    const sandbox = {
      ref,
      onLoad: callback => { onLoadHook = callback },
      onShow: callback => { onShowHook = callback },
      useAuthStore: () => ({ isLoggedIn: true, role: 'parent' }),
      listMonthlyReports: async params => {
        assert.equal(params.student_id, 21)
        assert.equal(params.month_label, '2026-09')
        return [chineseReport]
      },
    }
    const source = fs.readFileSync(new URL('../src/subParent/monthlyReports/useMonthlyReports.js', import.meta.url), 'utf8')
      .replace(/^import .*$/mg, '').replace('export function', 'function')
    vm.runInNewContext(`${source}\nglobalThis.view = useMonthlyReports()`, sandbox)
    onLoadHook({ studentId: '21', month: '2026-09', subject: subjectParam })
    await onShowHook()
    assert.equal(sandbox.view.error.value, '')
    assert.equal(sandbox.view.subject.value, '语文')
    const selected = monthlySubjects(sandbox.view.reports.value).find(item => item.subject === sandbox.view.subject.value)
    assert.equal(selected?.entries[0].content, '语文评定正文')
    // 不完整的转义字符不能令页面初始化崩溃。
    assert.doesNotThrow(() => onLoadHook({ studentId: '21', month: '2026-09', subject: '%E8%AF' }))
  })
}

test('月份倒序合并，同月多份报告只显示一个月份，未发布记录不进入家长列表', () => {
  const groups = monthlyGroups([report, { ...report, id: 2 }, { ...report, id: 3, month_label: '2026-10' }, { ...report, id: 4, status: 'generated', month_label: '2026-11' }])
  assert.deepEqual(groups.map(item => [item.month, item.label, item.subjectCount]), [
    ['2026-10', '2026年10月', 3], ['2026-09', '2026年9月', 3],
  ])
})

test('德育正文只出现一次，多科联合评定各科可达，空评定不展示', () => {
  const subjects = monthlySubjects([report])
  assert.deepEqual(subjects.map(item => item.subject), ['德育', '数学', '物理'])
  assert.equal(subjects[0].entries.length, 1)
  assert.equal(subjects[0].entries[0].content, '德育正文')
  assert.equal(subjects[1].entries[0].content, '联合评定')
  assert.equal(subjects[2].entries[0].content, '联合评定')
  assert.deepEqual(monthlySubjects([{ ...report, status: 'generated' }]), [])
})

test('历史班主任评价可兜底，同科多条内容完整保留', () => {
  const subjects = monthlySubjects([{ ...report, final_content: '' }, { ...report, id: 2 }])
  assert.equal(subjects[0].entries[0].content, '德育正文')
  assert.equal(subjects[1].entries.length, 2)
})

test('结构化正文分段显示，自由文本原样保留', () => {
  assert.deepEqual(reviewSections(formatReview({ summary: '本月进步\n继续保持', problems: '计算失误', plan: '每日练习' })).map(item => [item.label, item.content]), [
    ['总结', '本月进步\n继续保持'], ['问题', '计算失误'], ['计划', '每日练习'],
  ])
  const legacy = '历史正文\n含换行与【问题】字样'
  assert.deepEqual(reviewSections(legacy), [{ key: 'content', label: '评定内容', content: legacy }])
})
