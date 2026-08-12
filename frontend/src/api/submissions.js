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
