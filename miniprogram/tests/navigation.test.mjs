import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { ENTRIES, entriesForRole, groupsForRole } from '../src/utils/navigation.js'

test('菜单路由全部对应已注册的小程序页面', () => {
  const config = JSON.parse(fs.readFileSync(new URL('../src/pages.json', import.meta.url), 'utf8'))
  const routes = new Set([...config.pages.map(p => `/${p.path}`), ...config.subPackages.flatMap(pkg => pkg.pages.map(p => `/${pkg.root}/${p.path}`))])
  for (const entry of ENTRIES) assert.ok(routes.has(entry.route), entry.route)
})
test('访客与未知角色不显示业务入口', () => {
  assert.deepEqual(entriesForRole(''), [])
  assert.deepEqual(entriesForRole('unknown'), [])
})
test('家长和学生不出现教师写入入口，校长不出现德育审查操作', () => {
  for (const role of ['student', 'parent']) assert.ok(entriesForRole(role).every(e => !e.route.startsWith('/subTeacher/')))
  assert.ok(!entriesForRole('admin').some(e => e.route.includes('deyuReview')))
})
test('任课老师有档案入口，学生作业入口可达，各角色菜单不重复', () => {
  assert.ok(entriesForRole('subject_teacher').some(e => e.route === '/subTeacher/caseList/index'))
  assert.ok(entriesForRole('student').some(e => e.route === '/pages/student/assignments/index'))
  for (const role of ['student', 'parent', 'teacher', 'admin', 'deyu_director', 'consultant', 'subject_teacher']) {
    const entries = groupsForRole(role).flatMap(g => g.entries)
    assert.equal(new Set(entries.map(e => e.route)).size, entries.length)
    assert.ok(entries.length > 0)
  }
})
