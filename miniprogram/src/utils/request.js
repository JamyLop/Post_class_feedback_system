/**
 * uni.request 封装，复刻 frontend/src/api/index.js 的拦截器语义
 * - 注入 Authorization: Bearer <token>
 * - 401 自动清 token 并跳转 /pages/login/index
 * - 统一错误提示（uni.showToast）
 */
const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

// 真机 localhost 检测：mp 平台上 localhost 指向手机自身，必然不可达
const isMp = typeof uni !== 'undefined' && uni.getSystemInfoSync
let _warnedLocalhost = false
function warnIfLocalhostOnDevice() {
  if (_warnedLocalhost) return
  if (BASE_URL.includes('localhost') || BASE_URL.includes('127.0.0.1')) {
    try {
      const info = uni.getSystemInfoSync()
      // 开发者工具也上报，但仅在真机时提示更醒目
      const isDevtools = info.platform === 'devtools'
      if (!isDevtools) {
        console.warn('[request] VITE_API_BASE 仍为 localhost，真机无法访问本机服务，请改为局域网 IP 或 HTTPS 域名')
      }
    } catch (_) {}
    _warnedLocalhost = true
  }
}

function getToken() {
  try {
    return uni.getStorageSync('token') || ''
  } catch (_) {
    return ''
  }
}

function handleLogout() {
  try {
    uni.removeStorageSync('token')
    uni.removeStorageSync('user')
  } catch (_) {}
  // 避免在登录页重复跳转
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1]?.route || ''
  if (!cur.includes('pages/login/index')) {
    uni.reShowToast && uni.showToast({ title: '登录已过期', icon: 'none' })
    uni.reLaunch({ url: '/pages/login/index' })
  } else {
    uni.showToast({ title: '登录已过期', icon: 'none' })
  }
}

function request({ url, method = 'GET', data, header = {}, showError = true }) {
  warnIfLocalhostOnDevice()
  const token = getToken()
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...header,
      },
      success(res) {
        if (res.statusCode === 401) {
          handleLogout()
          reject({ status: 401, message: res.data?.detail || '未登录', data: res.data })
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const detail = res.data?.detail
          const msg = typeof detail === 'string' ? detail : res.errMsg || `请求失败(${res.statusCode})`
          if (showError) uni.showToast({ title: msg.slice(0, 40), icon: 'none' })
          reject({ status: res.statusCode, message: msg, data: res.data })
        }
      },
      fail(err) {
        let msg = err.errMsg || '网络异常'
        // localhost 在真机上常见 fail，需给出可操作提示
        if ((BASE_URL.includes('localhost') || BASE_URL.includes('127.0.0.1')) && msg.includes('request:fail')) {
          msg = '网络异常：真机无法访问 localhost，请配置 VITE_API_BASE 为局域网 IP 或线上 HTTPS'
        }
        if (showError) uni.showToast({ title: msg.slice(0, 40), icon: 'none' })
        reject({ status: 0, message: msg, data: null })
      },
    })
  })
}

export const http = {
  get(url, data, opts) {
    // uni.request GET 会把 data 转 queryString
    return request({ url, method: 'GET', data, ...(opts || {}) })
  },
  post(url, data, opts) { return request({ url, method: 'POST', data, ...(opts || {}) }) },
  put(url, data, opts) { return request({ url, method: 'PUT', data, ...(opts || {}) }) },
  patch(url, data, opts) { return request({ url, method: 'PATCH', data, ...(opts || {}) }) },
  del(url, data, opts) { return request({ url, method: 'DELETE', data, ...(opts || {}) }) },
}

export default http
