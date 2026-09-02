import { http } from '../utils/request'

export const listAssignments = (params = {}) => http.get('/assignments', params)
export const getAssignment = (id) => http.get(`/assignments/${id}`)
export const listSubmissions = (params = {}) => http.get('/submissions', params)
export const getSubmission = (id) => http.get(`/submissions/${id}`)
export const listWeeklyScores = (params = {}) => http.get('/weekly-test-scores', params)
export const getWeeklyTrend = (params = {}) => http.get('/weekly-test-scores/trend', params)
export const listMonthlyReports = (params = {}) => http.get('/monthly-reports', params)
