import http from './index'

export const listUsers = (role = 'student', keyword = '') =>
  http.get('/users', { params: { role, keyword } })
export const createUser = (data) => http.post('/users', data)
export const updateUser = (id, data) => http.put(`/users/${id}`, data)