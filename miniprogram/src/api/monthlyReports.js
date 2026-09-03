import { http } from '../utils/request'

// 查询月度评价列表
export const listMonthlyReports = (params) => http.get('/monthly-reports', params)

// 获取单个月度评价
export const getMonthlyReport = (id) => http.get(`/monthly-reports/${id}`)

// AI 生成月度评价
export const generateMonthlyReport = (data) => http.post('/monthly-reports/generate', data)

// 编辑月度评价
export const updateMonthlyReport = (id, data) => http.put(`/monthly-reports/${id}`, data)

// 发布月度评价
export const publishMonthlyReport = (id) => http.post(`/monthly-reports/${id}/publish`)

// 删除月度评价
export const deleteMonthlyReport = (id) => http.del(`/monthly-reports/${id}`)
