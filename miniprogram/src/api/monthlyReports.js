import { http } from '../utils/request'

// 查询月度评定列表
export const listMonthlyReports = (params) => http.get('/monthly-reports', params)

// 获取单个月度评定
export const getMonthlyReport = (id) => http.get(`/monthly-reports/${id}`)

// 手动新建月度评定
export const createMonthlyReport = (data) => http.post('/monthly-reports', data)

// 编辑月度评定
export const updateMonthlyReport = (id, data) => http.put(`/monthly-reports/${id}`, data)

// 发布月度评定
export const publishMonthlyReport = (id) => http.post(`/monthly-reports/${id}/publish`)

// 删除月度评定
export const deleteMonthlyReport = (id) => http.del(`/monthly-reports/${id}`)
