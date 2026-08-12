import http from './index'

export const listFeedback = (studentId, params) =>
  http.get(`/students/${studentId}/feedback`, { params })
export const generateFeedback = (studentId, data) =>
  http.post(`/students/${studentId}/feedback/generate`, data)
export const updateFeedback = (reportId, data) =>
  http.put(`/feedback/${reportId}`, data)
export const publishFeedback = (reportId) =>
  http.post(`/feedback/${reportId}/publish`)
