import http from './index'

export const listAssignments = () => http.get('/assignments')
export const getAssignment = (id) => http.get(`/assignments/${id}`)
export const createAssignment = (data) => http.post('/assignments', data)
export const updateAssignment = (id, data) => http.put(`/assignments/${id}`, data)
export const publishAssignment = (id) => http.post(`/assignments/${id}/publish`)
export const addQuestions = (id, questionIds) =>
  http.post(`/assignments/${id}/questions`, { question_ids: questionIds })
export const assignmentQuestions = (id) => http.get(`/assignments/${id}/questions`)
