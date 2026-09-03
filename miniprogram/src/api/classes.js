import { http } from '../utils/request'

// 班级列表
export const listClasses = () => http.get('/classes')

// 获取单个班级
export const getClass = (id) => http.get(`/classes/${id}`)

// 创建班级
export const createClass = (data) => http.post('/classes', data)

// 更新班级
export const updateClass = (id, data) => http.put(`/classes/${id}`, data)

// 删除班级
export const deleteClass = (id) => http.del(`/classes/${id}`)

// 班级学生列表
export const listClassStudents = (classId) => http.get(`/classes/${classId}/students`)

// 班级内新建学生并入班
export const createAndEnrollStudent = (classId, data) => http.post(`/classes/${classId}/students/create`, data)

// 批量添加已有学生到班级
export const addStudentsToClass = (classId, data) => http.post(`/classes/${classId}/students`, data)
