import http from './index'

export const createMonthlyReport = (data) => http.post('/monthly-reports', data)
export const listMonthlyReports = (params = {}) => http.get('/monthly-reports', { params })
export const getMonthlyReport = (id) => http.get(`/monthly-reports/${id}`)
export const updateMonthlyReport = (id, data) => http.put(`/monthly-reports/${id}`, data)
export const publishMonthlyReport = (id) => http.post(`/monthly-reports/${id}/publish`)
export const deleteMonthlyReport = (id) => http.delete(`/monthly-reports/${id}`)
