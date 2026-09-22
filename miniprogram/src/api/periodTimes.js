import { http } from '../utils/request'

// 课表读取时同步展示后台维护的节次时间；写入仍只对德育主任和校长开放。
export const listPeriodTimes = () => http.get('/period-times')

// 与网页端 updatePeriodTime 同接口：PUT /period-times/{period} { start_time, end_time }（HH:MM）
export const updatePeriodTime = (period, data) => http.put(`/period-times/${period}`, data)
