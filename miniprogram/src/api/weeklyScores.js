import { http } from '../utils/request'

// 查询月考成绩列表
export const listWeeklyScores = (params) => http.get('/monthly-exam-scores', params)

// 查询成绩趋势
export const getWeeklyTrend = (params) => http.get('/monthly-exam-scores/trend', params)

// 查询班级汇总
export const getClassSummary = (params) => http.get('/monthly-exam-scores/class-summary', params)

// 单条录入
export const createWeeklyScore = (data) => http.post('/monthly-exam-scores', data)

// 批量录入
export const batchCreateWeeklyScores = (data) => http.post('/monthly-exam-scores/batch', data)

// 修改成绩
export const updateWeeklyScore = (id, data) => http.put(`/monthly-exam-scores/${id}`, data)

// 删除成绩
export const deleteWeeklyScore = (id) => http.del(`/monthly-exam-scores/${id}`)
export const saveWeeklyEvaluation = (id, data) => http.put(`/monthly-exam-scores/${id}/evaluation`, data)
