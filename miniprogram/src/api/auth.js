import { http } from '../utils/request'

export const login = (username, password) => http.post('/auth/login', { username, password })
export const register = (data) => http.post('/auth/register', data)
export const getMe = () => http.get('/auth/me')
export const getMyChildren = () => http.get('/auth/me/children')
export const wxLogin = (code) => http.post('/auth/wx-login', { code })
export const wxBind = (data) => http.post('/auth/wx-bind', data)
export const wxUnbind = () => http.post('/auth/wx-unbind', {})
