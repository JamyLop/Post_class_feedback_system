import http from './index'

export const submitAssignment = (assignmentId, formData) =>
  http.post(`/assignments/${assignmentId}/submit`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const getSubmission = (id) => http.get(`/submissions/${id}`)
export const listSubmissions = (assignmentId) =>
  http.get(`/assignments/${assignmentId}/submissions`)
