import http from './index'

export const listUsers = (role = 'student', keyword = '') =>
  http.get('/users', { params: { role, keyword } })
export const createUser = (data) => http.post('/users', data)
export const createQuickStudent = (data) => http.post('/users/quick-student', data)
export const updateUser = (id, data) => http.put(`/users/${id}`, data)
export const listConsultantStudents = (params = {}) => http.get('/users/consultant-students', { params })
export const linkConsultantStudent = (studentId) => http.post('/users/consultant-students', { student_id: studentId })
