import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'

const source = fs.readFileSync(new URL('../src/pages/login/index.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/gm, '')

async function openLogin({ token = '', role = 'teacher', failure } = {}) {
  const routes = []
  let captchaRequests = 0
  let mounted
  let restores = 0
  const auth = {
    token,
    restore() { restores++; if (failure?.status === 401 && restores > 1) this.token = '' },
    async refreshMe() { if (failure) throw failure; return { role } },
  }
  const context = vm.createContext({
    ref: value => ({ value }), reactive: value => value,
    onMounted: callback => { mounted = callback }, useAuthStore: () => auth,
    getCaptcha: async () => { captchaRequests++; return { captcha_id: 'test', image: 'image' } },
    uni: { reLaunch: ({ url }) => routes.push(url), showToast() {} },
  })
  vm.runInContext(script, context)
  await mounted()
  return { routes, captchaRequests, auth, restoring: vm.runInContext('restoringSession.value', context) }
}

test('有效缓存会话跳过验证码，按最新角色进入工作台', async () => {
  for (const role of ['teacher', 'subject_teacher', 'admin', 'student', 'parent']) {
    const result = await openLogin({ token: 'cached-token', role })
    assert.deepEqual(result.routes, [['student', 'parent'].includes(role) ? '/subParent/children/index' : '/pages/index/index'])
    assert.equal(result.captchaRequests, 0)
  }
})

test('首次登录和主动退出后需要验证', async () => {
  const result = await openLogin()
  assert.deepEqual(result.routes, [])
  assert.equal(result.captchaRequests, 1)
  assert.equal(result.restoring, false)
})

test('过期或停用会话回到验证流程', async () => {
  const result = await openLogin({ token: 'expired-token', failure: { status: 401 } })
  assert.equal(result.auth.token, '')
  assert.deepEqual(result.routes, [])
  assert.equal(result.captchaRequests, 1)
  assert.equal(result.restoring, false)
})

test('网络故障不会删除已有登录信息', async () => {
  const result = await openLogin({ token: 'cached-token', failure: { status: 0 } })
  assert.equal(result.auth.token, 'cached-token')
  assert.deepEqual(result.routes, [])
  assert.equal(result.restoring, false)
})

test('账号密码登录请求声明小程序，刷新资料不改写令牌', async () => {
  const storeSource = fs.readFileSync(new URL('../src/stores/auth.js', import.meta.url), 'utf8')
    .replace(/^import .*$/gm, '').replace('export const useAuthStore', 'const useAuthStore')
  const requests = []
  const cache = new Map()
  const context = vm.createContext({
    defineStore: (_id, options) => () => Object.assign(options.state(), options.actions),
    http: {
      post: async (url, body) => { requests.push({ url, body }); return { access_token: 'weekly-token', user: { role: 'teacher' } } },
      get: async () => ({ role: 'teacher' }),
    },
    uni: { setStorageSync: (key, value) => cache.set(key, value), getStorageSync: key => cache.get(key) },
  })
  vm.runInContext(storeSource + '\nvar auth = useAuthStore()', context)
  await vm.runInContext("auth.login('user', 'password', 'captcha-id', 'captcha-code')", context)
  assert.equal(requests[0].body.client, 'miniprogram')
  assert.deepEqual([...cache.keys()].sort(), ['token', 'user'])
  await vm.runInContext('auth.refreshMe()', context)
  assert.equal(cache.get('token'), 'weekly-token')
})
