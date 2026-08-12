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

export async function openSubmissionFile(path) {
  // 先同步打开空标签，避免鉴权下载完成后被浏览器当作弹窗拦截。
  const target = window.open('about:blank', '_blank')
  if (target) target.opener = null
  try {
    const blob = await http.get(`/storage/files/${path}`, { responseType: 'blob' })
    const url = URL.createObjectURL(blob)
    if (target) target.location.href = url
    else window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (error) {
    if (target) target.close()
    throw error
  }
}
