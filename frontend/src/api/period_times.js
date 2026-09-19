import http from './index'

export const listPeriodTimes = () => http.get('/period-times')
export const updatePeriodTime = (period, data) => http.put(`/period-times/${period}`, data)
