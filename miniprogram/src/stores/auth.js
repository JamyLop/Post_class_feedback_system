import { defineStore } from 'pinia'
import { http } from '../utils/request'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    user: null,
    bindTicket: '', // wx-login 未绑定时返回的一次性票据
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    role: (s) => s.user?.role || '',
  },
  actions: {
    restore() {
      try {
        this.token = uni.getStorageSync('token') || ''
        const raw = uni.getStorageSync('user')
        this.user = raw ? JSON.parse(raw) : null
      } catch (_) {}
    },
    async login(username, password) {
      const data = await http.post('/auth/login', { username, password })
      this.token = data.access_token
      this.user = data.user
      uni.setStorageSync('token', data.access_token)
      uni.setStorageSync('user', JSON.stringify(data.user))
      return data.user
    },
    async wxLogin(code) {
      // 后端 POST /api/auth/wx-login { code }
      const data = await http.post('/auth/wx-login', { code })
      if (data.access_token) {
        this.token = data.access_token
        this.user = data.user
        uni.setStorageSync('token', data.access_token)
        uni.setStorageSync('user', JSON.stringify(data.user))
        this.bindTicket = ''
        return { bound: true, user: data.user }
      }
      // 未绑定：返回 bind_ticket
      this.bindTicket = data.bind_ticket || ''
      return { bound: false, bind_ticket: data.bind_ticket }
    },
    async wxBind({ bind_ticket, username, password, invite_code, role, name }) {
      const ticket = bind_ticket || this.bindTicket
      const payload = ticket ? { bind_ticket: ticket, username, password, invite_code, role, name } : { username, password }
      // 兼容两种绑定：已有账号 vs 邀请码注册（由后端区分）
      const data = await http.post('/auth/wx-bind', payload)
      this.token = data.access_token
      this.user = data.user
      uni.setStorageSync('token', data.access_token)
      uni.setStorageSync('user', JSON.stringify(data.user))
      this.bindTicket = ''
      return data.user
    },
    async refreshMe() {
      const user = await http.get('/auth/me')
      this.user = user
      uni.setStorageSync('user', JSON.stringify(user))
      return user
    },
    async wxUnbind() {
      await http.post('/auth/wx-unbind', {})
      uni.showToast({ title: '已解绑', icon: 'success' })
    },
    logout() {
      this.token = ''
      this.user = null
      this.bindTicket = ''
      try {
        uni.removeStorageSync('token')
        uni.removeStorageSync('user')
      } catch (_) {}
      uni.reLaunch({ url: '/pages/login/index' })
    },
  },
})
