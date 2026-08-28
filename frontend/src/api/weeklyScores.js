import http from './index'

export const listWeeklyScores = (params = {}) => http.get('/weekly-test-scores', { params })
export const getWeeklyTrend = (params = {}) => http.get('/weekly-test-scores/trend', { params })
export const getClassWeeklySummary = (params = {}) => http.get('/weekly-test-scores/class-summary', { params })
export const createWeeklyScore = (data) => http.post('/weekly-test-scores', data)
export const batchCreateWeeklyScores = (data) => http.post('/weekly-test-scores/batch', data)
export const updateWeeklyScore = (id, data) => http.put(`/weekly-test-scores/${id}`, data)
export const deleteWeeklyScore = (id) => http.delete(`/weekly-test-scores/${id}`)
