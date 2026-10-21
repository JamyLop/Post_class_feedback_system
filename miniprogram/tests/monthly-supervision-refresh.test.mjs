import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import { createRequire } from 'node:module'

const pages = [
  { name: 'Web', path: '../../frontend/src/views/subject/SubjectMonthlyReports.vue', package: '../../frontend/package.json' },
  { name: '小程序', path: '../src/subTeacher/monthlyReports/index.vue', package: '../package.json' },
]
const own = [{ id: 20, name: '本人任教班级' }]
const stageClasses = [{ id: 10, name: '学段其他班级' }, ...own]
const deferred = () => {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
const settle = async () => {
  for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve))
}

function mountPage(t, page, initialStage = '') {
  const vue = createRequire(new URL(page.package, import.meta.url))('vue')
  const scope = vue.effectScope()
  t.after(() => scope.stop())
  const calls = { own: 0, stage: 0, writing: 0, reports: [], errors: [] }
  const auth = vue.reactive({
    isLoggedIn: true,
    role: 'subject_teacher',
    user: { supervisor_stage: initialStage },
    async refreshMe() { auth.user = await api.identity(); return auth.user },
  })
  const api = {
    identity: async () => ({ supervisor_stage: initialStage }),
    own: async () => own,
    stage: async () => stageClasses,
  }
  let lifecycle
  const sandbox = {
    ...vue,
    onMounted: callback => { lifecycle = callback },
    onShow: callback => { lifecycle = callback },
    useAuthStore: () => auth,
    listClasses: async () => { calls.own++; return api.own() },
    listSupervisionClasses: async () => { calls.stage++; return api.stage() },
    listMonthlyReports: async params => { calls.reports.push({ ...params }); return [] },
    ElMessage: { error: message => calls.errors.push(message) },
    uni: { showToast: value => calls.errors.push(value.title), reLaunch() {} },
  }
  const source = fs.readFileSync(new URL(page.path, import.meta.url), 'utf8')
  const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/mg, '')
  // 执行真实页面的异步流程和 Vue watcher，不依赖模拟的加载顺序。
  const bindings = page.name === 'Web'
    ? 'classes, teachingClasses, filters'
    : 'classes: classList, teachingClasses: teachingClassList, classIndex, selectedClassId'
  scope.run(() => vm.runInNewContext(`${script}\n;globalThis.page = { ${bindings}, writingQuery, refreshPage };`, sandbox))
  sandbox.page.writingQuery.value = { load() { calls.writing++ } }
  return { ...sandbox.page, auth, api, calls, lifecycle }
}

const ids = page => Array.from(page.classes.value, row => row.id)
const selectedId = page => page.filters ? page.filters.value.class_id : page.selectedClassId.value
for (const page of pages) {
  test(`${page.name}：同步主管身份后，教学入口仍只加载任教班级`, async t => {
    const view = mountPage(t, page)
    const identity = deferred()
    view.api.identity = () => identity.promise
    const opening = view.lifecycle()
    await settle()
    assert.equal(view.calls.own, 0)
    assert.equal(view.calls.stage, 0)
    identity.resolve({ supervisor_stage: '初中' })
    await opening
    assert.deepEqual(ids(view), [20])
    assert.deepEqual(Array.from(view.teachingClasses.value, row => row.id), [20])
    assert.equal(selectedId(view), page.name === 'Web' ? 20 : null)
    assert.equal(view.calls.stage, 0)
    assert.ok(view.calls.reports.every(params => !params.class_id || params.class_id === 20))
  })

  test(`${page.name}：授予、撤销主管身份均不扩大学科评定班级范围`, async t => {
    const view = mountPage(t, page)
    await view.lifecycle()
    view.auth.user = { supervisor_stage: '初中' }
    await settle()
    assert.deepEqual(ids(view), [20])
    view.auth.user = { supervisor_stage: '' }
    await settle()
    assert.deepEqual(ids(view), [20])
    assert.notEqual(selectedId(view), 10)
    assert.equal(view.calls.stage, 0)
    assert.ok(view.calls.writing >= 3)
  })

  test(`${page.name}：手动刷新会同步刚授予的身份，且不重复加载范围`, async t => {
    const view = mountPage(t, page)
    await view.lifecycle()
    view.api.identity = async () => ({ supervisor_stage: '高中' })
    const before = view.calls.own
    await view.refreshPage()
    await settle()
    assert.deepEqual(ids(view), [20])
    assert.equal(selectedId(view), page.name === 'Web' ? 20 : null)
    assert.equal(view.calls.stage, 0)
    assert.equal(view.calls.own - before, 1)
  })

  test(`${page.name}：身份刷新失败时提示重试，不按旧主管缓存继续查询`, async t => {
    const view = mountPage(t, page, '初中')
    view.api.identity = async () => { throw new Error('offline') }
    await view.lifecycle()
    assert.equal(view.calls.errors.length, 1)
    assert.equal(view.calls.own, 0)
    assert.equal(view.calls.stage, 0)
    assert.equal(view.calls.reports.length, 0)
  })

  test(`${page.name}：任教班级慢请求不能覆盖最新班级范围`, async t => {
    const view = mountPage(t, page)
    await view.lifecycle()
    const stale = deferred()
    view.api.own = () => stale.promise
    view.auth.user = { supervisor_stage: '初中' }
    await settle()
    assert.equal(view.calls.own, 2)
    view.api.own = async () => own
    view.auth.user = { supervisor_stage: '' }
    await settle()
    assert.deepEqual(ids(view), [20])
    stale.resolve([{ id: 30, name: '原任教班级' }])
    await settle()
    assert.deepEqual(ids(view), [20])
    assert.deepEqual(Array.from(view.teachingClasses.value, row => row.id), [20])
  })
}

test('小程序：返回页面时班级顺序变化，仍按班级 ID 保留原选择', async t => {
  const view = mountPage(t, pages[1], '初中')
  view.api.own = async () => [{ id: 30, name: '本人第二个任教班级' }, ...own]
  await view.lifecycle()
  view.classIndex.value = 2
  assert.equal(selectedId(view), 20)
  view.api.own = async () => [...own, { id: 30, name: '本人第二个任教班级' }]
  await view.lifecycle()
  assert.deepEqual(ids(view), [20, 30])
  assert.equal(selectedId(view), 20)
  assert.equal(view.calls.reports.at(-1).class_id, 20)
})
