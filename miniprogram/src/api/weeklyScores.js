import { http } from '../utils/request'

// 查询周测成绩列表
export const listWeeklyScores = (params) => http.get('/weekly-test-scores', params)

// 查询成绩趋势
export const getWeeklyTrend = (params) => http.get('/weekly-test-scores/trend', params)

// 查询班级汇总
export const getClassSummary = (params) => http.get('/weekly-test-scores/class-summary', params)

// 单条录入
export const createWeeklyScore = (data) => http.post('/weekly-test-scores', data)

// 批量录入
export const batchCreateWeeklyScores = (data) => http.post('/weekly-test-scores/batch', data)

// 修改成绩
export const updateWeeklyScore = (id, data) => http.put(`/weekly-test-scores/${id}`, data)

// 删除成绩
export const deleteWeeklyScore = (id) => http.del(`/weekly-test-scores/${id}`)
export const saveWeeklyEvaluation = (id, data) => http.put(`/weekly-test-scores/${id}/evaluation`, data)
