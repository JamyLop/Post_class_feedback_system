import { http } from '../utils/request'

export const getCaptcha = () => http.get('/auth/captcha')
export const login = (username, password, captcha_id = '', captcha_code = '') =>
  http.post('/auth/login', { username, password, captcha_id, captcha_code })
export const register = (data) => http.post('/auth/register', data)
export const getMe = () => http.get('/auth/me')
export const getMyChildren = () => http.get('/auth/me/children')
export const wxLogin = (code) => http.post('/auth/wx-login', { code })
export const wxBind = (data) => http.post('/auth/wx-bind', data)
export const wxUnbind = () => http.post('/auth/wx-unbind', {})
