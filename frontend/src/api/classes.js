import http from './index'

export const listClasses = () => http.get('/classes')
export const createClass = (data) => http.post('/classes', data)
export const updateClass = (id, data) => http.put(`/classes/${id}`, data)
export const deleteClass = (id) => http.delete(`/classes/${id}`)
export const getClass = (id) => http.get(`/classes/${id}`)
export const listStudents = (classId) => http.get(`/classes/${classId}/students`)
export const addStudents = (classId, studentIds) =>
  http.post(`/classes/${classId}/students`, { student_ids: studentIds })
export const createStudentAndAdd = (classId, data) =>
  http.post(`/classes/${classId}/students/create`, data)

export const listUsers = (role = 'student', keyword = '') =>
  http.get('/users', { params: { role, keyword } })
export const createUser = (data) => http.post('/users', data)
