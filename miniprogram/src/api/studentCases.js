import { http } from '../utils/request'

export const listStudentCases = (params = {}) => http.get('/student-cases', params)
export const listCaseCycles = () => http.get('/student-cases/cycles')
export const getStudentCase = (id) => http.get(`/student-cases/${id}`)
export const getFamilyCases = () => http.get('/student-cases/children')
export const getCaseProgress = (params = {}) => http.get('/student-cases/progress', params)
export const getCaseVersions = (caseId) => http.get(`/student-cases/${caseId}/versions`)
export const getMyChildren = () => http.get('/auth/me/children')

// 家长只读不需要的写接口在小程序教师端按需开放
export const createCaseReview = (caseId, data) => http.post(`/student-cases/${caseId}/reviews`, data)
export const checkinCaseTask = (taskId, data) => http.post(`/student-cases/tasks/${taskId}/checkins`, data)
