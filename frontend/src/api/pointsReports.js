import http from './index'

export const listPointsReports = (params = {}) => http.get('/points-reports', { params })
export const buildPointsReports = (data) => http.post('/points-reports/build', data)
