import http from './index'

export const getMonthlyExamEntryOptions = () => http.get('/monthly-exam-scores/entry-options')

export const getMonthlyExamOverview = (params = {}) => http.get('/monthly-exam-scores/overview', { params })
export const exportMonthlyExamOverview = (params = {}) => http.get('/monthly-exam-scores/overview/export', { params, responseType: 'blob' })

export const listWeeklyScores = (params = {}) => http.get('/monthly-exam-scores', { params })
export const getWeeklyTrend = (params = {}) => http.get('/monthly-exam-scores/trend', { params })
export const getClassWeeklySummary = (params = {}) => http.get('/monthly-exam-scores/class-summary', { params })
export const createWeeklyScore = (data) => http.post('/monthly-exam-scores', data)
export const batchCreateWeeklyScores = (data) => http.post('/monthly-exam-scores/batch', data)
export const updateWeeklyScore = (id, data) => http.put(`/monthly-exam-scores/${id}`, data)
export const deleteWeeklyScore = (id) => http.delete(`/monthly-exam-scores/${id}`)
export const saveWeeklyEvaluation = (id, data) => http.put(`/monthly-exam-scores/${id}/evaluation`, data)
