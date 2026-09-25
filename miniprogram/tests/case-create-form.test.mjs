import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('../src/subTeacher/caseList/index.vue', import.meta.url), 'utf8')
const editSource = fs.readFileSync(new URL('../src/subTeacher/caseEdit/index.vue', import.meta.url), 'utf8')
const protectedModalFiles = [
  'adminUsers/index.vue',
  'consultantLinks/index.vue',
  'subjectLinks/index.vue',
  'taskManager/index.vue',
]

test('新建档案输入时遮罩层不会关闭表单', () => {
  const maskTag = source.match(/<view v-if="createVisible" class="modal-mask"[^>]*>/)?.[0] || ''
  assert.ok(maskTag, '未找到新建档案遮罩层')
  assert.ok(!maskTag.includes('@click'), '遮罩层不应绑定关闭事件，原生 textarea 聚焦可能误触发')

  for (const field of ['parent_evaluation', 'primary_needs', 'current_summary']) {
    assert.match(source, new RegExp(`<textarea[^>]+v-model="createForm\\.${field}"`))
  }
  assert.match(source, /class="modal-close" @click="createVisible=false"/)
  assert.match(source, /class="btn-outline" @click="createVisible=false"/)
})

test('学科方案输入时遮罩层不会关闭编辑弹层', () => {
  const maskTag = editSource.match(/<view v-if="showPlanForm" class="modal-mask"[^>]*>/)?.[0] || ''
  assert.ok(maskTag, '未找到学科方案编辑遮罩层')
  assert.ok(!maskTag.includes('@click'), '遮罩层不应绑定关闭事件，原生 textarea 聚焦可能误触发')

  for (const field of ['problem_location', 'cause_analysis', 'struggle_goal', 'gaokao_requirement', 'reinforcement']) {
    assert.match(editSource, new RegExp(`<textarea[^>]+v-model="planForm\\.${field}"`))
  }
  assert.match(editSource, /class="modal-close" @click="showPlanForm=false"/)
  assert.match(editSource, /class="btn-outline" @click="showPlanForm=false"/)
})

test('其他角色的表单弹层也不会被遮罩误关闭', () => {
  for (const relativePath of protectedModalFiles) {
    const modalSource = fs.readFileSync(new URL(`../src/subTeacher/${relativePath}`, import.meta.url), 'utf8')
    const maskTags = [...modalSource.matchAll(/<view[^>]+class="modal-mask"[^>]*>/g)].map(match => match[0])
    assert.ok(maskTags.length, `${relativePath} 未找到表单遮罩层`)
    for (const maskTag of maskTags) {
      assert.ok(!maskTag.includes('@click.self'), `${relativePath} 的遮罩层不应绑定点击关闭事件`)
      assert.ok(!maskTag.includes('@tap.self'), `${relativePath} 的遮罩层不应绑定点击关闭事件`)
    }
  }
})
