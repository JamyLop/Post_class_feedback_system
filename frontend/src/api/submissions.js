import http from './index'

export const submitAssignment = (assignmentId, formData) =>
  http.post(`/assignments/${assignmentId}/submit`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const getSubmission = (id) => http.get(`/submissions/${id}`)
export const getSubmissionGrading = (id) => http.get(`/submissions/${id}/grading`)
export const retryGrading = (gradingId) => http.post(`/gradings/${gradingId}/retry`)
export const listSubmissions = (assignmentId) =>
  http.get(`/assignments/${assignmentId}/submissions`)
export const listReviews = (params) => http.get('/reviews', { params })
export const confirmGrading = (gradingId, data) =>
  http.put(`/gradings/${gradingId}/confirm`, data)
export const flagGrading = (gradingId, data) =>
  http.post(`/gradings/${gradingId}/flag`, data)
export const confirmAllGrading = (submissionId) =>
  http.post(`/submissions/${submissionId}/confirm-all`)
