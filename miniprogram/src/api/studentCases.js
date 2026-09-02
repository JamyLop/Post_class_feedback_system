import { http } from '../utils/request'

// ---- 班级 ----
export const listClasses = () => http.get('/classes')
export const listClassStudents = (classId) => http.get(`/classes/${classId}/students`)

// ---- 一生一案：查询 ----
export const listStudentCases = (params = {}) => http.get('/student-cases', params)
export const listCaseCycles = () => http.get('/student-cases/cycles')
export const getStudentCase = (id) => http.get(`/student-cases/${id}`)
export const getFamilyCases = () => http.get('/student-cases/children')
export const getCaseProgress = (params = {}) => http.get('/student-cases/progress', params)
export const getCaseVersions = (caseId) => http.get(`/student-cases/${caseId}/versions`)
export const getMyChildren = () => http.get('/auth/me/children')
export const getMyCase = () => http.get('/student-cases/my-case')

// ---- 一生一案：写操作（班主任） ----
export const createStudentCase = (data) => http.post('/student-cases', data)
export const updateStudentCase = (caseId, data) => http.patch(`/student-cases/${caseId}`, data)
export const transitionCase = (caseId, data) => http.post(`/student-cases/${caseId}/transition`, data)
export const upsertSubjectPlan = (caseId, subject, data) => http.put(`/student-cases/${caseId}/subject-plans/${encodeURIComponent(subject)}`, data)
export const createGoal = (caseId, data) => http.post(`/student-cases/${caseId}/goals`, data)
export const createTask = (caseId, data) => http.post(`/student-cases/${caseId}/tasks`, data)
export const updateTask = (caseId, taskId, data) => http.put(`/student-cases/${caseId}/tasks/${taskId}`, data)
export const checkinCaseTask = (taskId, data) => http.post(`/student-cases/tasks/${taskId}/checkins`, data)
export const createCaseReview = (caseId, data) => http.post(`/student-cases/${caseId}/reviews`, data)
