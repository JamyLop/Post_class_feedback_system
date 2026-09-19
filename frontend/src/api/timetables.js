import http from './index'

export const listTimetable = (params = {}) => http.get('/timetables', { params })
export const myTimetable = () => http.get('/timetables/mine')
export const createTimetableEntry = (data) => http.post('/timetables', data)
export const updateTimetableEntry = (id, data) => http.put(`/timetables/${id}`, data)
export const deleteTimetableEntry = (id) => http.delete(`/timetables/${id}`)
