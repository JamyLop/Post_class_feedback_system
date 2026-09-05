import http from './index'

export const listQuestions = (params) => http.get('/questions', { params })
export const createQuestion = (data) => http.post('/questions', data)
export const getQuestion = (id) => http.get(`/questions/${id}`)
export const updateQuestion = (id, data) => http.put(`/questions/${id}`, data)

export const parseQuestions = (formData) =>
  http.post('/questions/parse', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const batchCreateQuestions = (questions) =>
  http.post('/questions/batch', { questions })

export const kpTree = () => http.get('/knowledge-points/tree')
export const listKnowledgePoints = () => http.get('/knowledge-points')
export const createKnowledgePoint = (data) => http.post('/knowledge-points', data)
