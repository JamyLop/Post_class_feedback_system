import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import { computed, ref } from 'vue'

const source = fs.readFileSync(new URL('../src/subTeacher/classManager/index.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/mg, '')

function mountPage(role = 'deyu_director') {
  const calls = { updates: [], toasts: [], navigation: [] }
  const api = { update: async (id, body) => ({ id, name: body.name }) }
  const sandbox = {
    ref, computed, onShow() {}, useAuthStore: () => ({ role, isLoggedIn: true }),
    CLASS_MANAGEMENT_ROLES: [], listClasses: async () => [],
    updateClass: async (id, body) => { calls.updates.push({ id, ...body }); return api.update(id, body) },
    uni: { showToast: value => calls.toasts.push(value.title), navigateTo: value => calls.navigation.push(value.url) },
  }
  vm.runInNewContext(`${script}\n;globalThis.page = { classList, canManageClass, editingClassId, renameName, renaming, startRename, cancelRename, saveRename, goStudents };`, sandbox)
  const page = sandbox.page
  page.classList.value = [{ id: 1, name: '高三1班', teacher_id: 2, school_year: '2026-2027' }]
  return { page, cls: page.classList.value[0], calls, api }
}

for (const role of ['deyu_director', 'admin']) {
  test(`${role}：只提交名称，更新显示及学生名册导航`, async () => {
    const { page, cls, calls } = mountPage(role)
    page.startRename(cls)
    page.renameName.value = '  高三实验班  '
    await page.saveRename(cls)
    assert.equal(JSON.stringify(calls.updates), JSON.stringify([{ id: 1, name: '高三实验班' }]))
    assert.equal(cls.name, '高三实验班')
    assert.equal(cls.teacher_id, 2)
    assert.equal(cls.school_year, '2026-2027')
    assert.equal(page.editingClassId.value, null)
    page.goStudents(cls.id, cls.name)
    assert.ok(calls.navigation[0].includes(encodeURIComponent('高三实验班')))
  })
}

for (const role of ['teacher', 'subject_teacher', 'consultant', 'student', 'parent']) {
  test(`${role}：不能开启或提交名称修改`, async () => {
    const { page, cls, calls } = mountPage(role)
    assert.equal(page.canManageClass.value, false)
    page.startRename(cls)
    assert.equal(page.editingClassId.value, null)
    page.editingClassId.value = cls.id
    page.renameName.value = '无权更名'
    await page.saveRename(cls)
    assert.equal(calls.updates.length, 0)
  })
}

test('取消、名称未变、空白和超长输入均不请求更新', async () => {
  const { page, cls, calls } = mountPage()
  page.startRename(cls)
  page.renameName.value = '取消的修改'
  page.cancelRename()
  assert.equal(cls.name, '高三1班')
  assert.equal(page.editingClassId.value, null)
  for (const name of ['高三1班', '   ', '班'.repeat(65)]) {
    page.startRename(cls)
    page.renameName.value = name
    await page.saveRename(cls)
  }
  assert.equal(calls.updates.length, 0)
  assert.equal(calls.toasts.length, 2)
})

test('保存期间防止重复提交，失败后保留输入并允许重试', async () => {
  const { page, cls, calls, api } = mountPage()
  let rejectUpdate
  api.update = () => new Promise((resolve, reject) => { rejectUpdate = reject })
  page.startRename(cls)
  page.renameName.value = '新班名'
  const pending = page.saveRename(cls)
  assert.equal(page.renaming.value, true)
  await page.saveRename(cls)
  page.cancelRename()
  assert.equal(calls.updates.length, 1)
  assert.equal(page.editingClassId.value, cls.id)
  rejectUpdate(new Error('network error'))
  await pending
  assert.equal(page.renaming.value, false)
  assert.equal(page.renameName.value, '新班名')
  assert.equal(cls.name, '高三1班')
  api.update = async () => ({ name: '新班名' })
  await page.saveRename(cls)
  assert.equal(cls.name, '新班名')
  assert.equal(page.editingClassId.value, null)
})
