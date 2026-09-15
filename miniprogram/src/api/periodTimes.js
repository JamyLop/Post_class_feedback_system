import { http } from '../utils/request'

// 课表读取时同步展示后台维护的节次时间；写入仍只对德育主任和校长开放。
export const listPeriodTimes = () => http.get('/period-times')
