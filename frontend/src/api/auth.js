import http from './index'

export const getCaptcha = () => http.get('/auth/captcha')
export const login = (username, password, captcha_id = '', captcha_code = '') =>
  http.post('/auth/login', { username, password, captcha_id, captcha_code })
export const getMe = () => http.get('/auth/me')
export const register = (data) => http.post('/auth/register', data)
