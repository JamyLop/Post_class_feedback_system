import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const pages = [
  '../src/pages/login/index.vue',
  '../src/pages/register/index.vue',
  '../../frontend/src/views/Login.vue',
  '../../frontend/src/views/Register.vue',
]

for (const relativePath of pages) {
  test(`${relativePath} 等待验证码刷新并合并并发请求`, () => {
    const source = fs.readFileSync(new URL(relativePath, import.meta.url), 'utf8')
    assert.match(source, /let captchaRequest = null/)
    assert.match(source, /if \(captchaRequest\) return captchaRequest/)
    assert.match(source, /await fetchCaptcha\(\)/)
    assert.match(source, /captchaLoading/)
    assert.match(source, /验证码尚未加载，请点击刷新/)
  })
}
