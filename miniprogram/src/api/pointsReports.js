import { http } from '../utils/request'

// 积分周报/月报：仅班主任 / 德育主任 / 管理员可见可建（后端 403 兜底）
export const listPointsReports = (params = {}) => http.get('/points-reports', params)
export const buildPointsReports = (data) => http.post('/points-reports/build', data)
