const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

// 直接执行组件、API 和请求封装，检查传入 uni.request 的 data，避免 H5
// 自动丢弃 undefined 而掩盖微信 GET 参数序列化差异。
const root = path.resolve(__dirname, '..')
const calls = []
const sandbox = {
  console,
  ref: value => ({ value }),
  computed: getter => ({ get value() { return getter() } }),
  onMounted() {},
  defineProps: () => ({ classes: [{ id: 7, name: '测试班级' }] }),
  defineExpose() {},
  uni: {
    getStorageSync: () => '',
    request(options) {
      calls.push(options)
      options.success({ statusCode: 200, data: { total: 0, written: 0, unwritten: 0, filtered_total: 0, student_total: 0, items: [], students: [] } })
    },
  },
}
vm.createContext(sandbox)
let request = fs.readFileSync(path.join(root, 'src/utils/request.js'), 'utf8')
request = request.replace('import.meta.env.VITE_API_BASE', JSON.stringify('https://fixture.invalid/api')).replace(/export default http/, '').replace(/export (const|function) /g, '$1 ')
vm.runInContext(request, sandbox)
let api = fs.readFileSync(path.join(root, 'src/api/monthlyReports.js'), 'utf8').replace(/^import .*$/mg, '').replace(/export const /g, 'const ')
vm.runInContext(api, sandbox)
const source = fs.readFileSync(path.join(root, 'src/components/MonthlyWritingStatus.vue'), 'utf8')
vm.runInContext(source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/mg, ''), sandbox)

async function run(statement) {
  await vm.runInContext(statement, sandbox)
  const { data } = calls.at(-1)
  assert.ok(Object.values(data).every(value => value !== undefined && value !== null))
  const query = new URLSearchParams(data).toString()
  assert.ok(!query.includes('undefined') && !query.includes('null'))
  return data
}

;(async () => {
  const initial = await run('load()')
  assert.equal(initial.view, 'students')
  assert.ok(!Object.hasOwn(initial, 'student_id'))
  assert.equal(initial.keyword, '')
  const filtered = await run("keyword.value = ' 测试学生 '; classIndex.value = 1; statusIndex.value = 2; load()")
  assert.equal(filtered.keyword, '测试学生')
  assert.equal(filtered.class_id, 7)
  assert.equal(filtered.writing_status, 'unwritten')
  const detail = await run('selectedStudent.value = { student_id: 21, class_id: 7 }; load()')
  assert.equal(detail.student_id, 21)
  assert.equal(detail.view, 'items')
  assert.ok(!Object.hasOwn(detail, 'keyword'))
  assert.ok(!Object.hasOwn(detail, 'writing_status'))
  const back = await run('selectedStudent.value = null; load()')
  assert.equal(back.view, 'students')
  assert.ok(!Object.hasOwn(back, 'student_id'))
  assert.equal(back.keyword, '测试学生')
  console.log('PASS: summary, filters, subject detail, and return requests contain no undefined/null query parameters')
})().catch(error => { console.error(error); process.exitCode = 1 })
