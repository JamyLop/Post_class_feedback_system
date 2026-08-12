import http from './index'

export const getStudentKnowledgeStats = (studentId, params) =>
  http.get(`/students/${studentId}/knowledge-stats`, { params })
export const getStudentWeakPoints = (studentId, params) =>
  http.get(`/students/${studentId}/weak-points`, { params })
export const getStudentLearningTrend = (studentId, params) =>
  http.get(`/students/${studentId}/learning-trend`, { params })
export const getStudentRepeatedErrors = (studentId, params) =>
  http.get(`/students/${studentId}/repeated-errors`, { params })
export const recomputeStudentStats = (studentId, params) =>
  http.post(`/students/${studentId}/knowledge-stats/recompute`, null, { params })
export const getAssignmentAnalysis = (assignmentId) =>
  http.get(`/assignments/${assignmentId}/analysis`)
export const getClassAnalytics = (classId) =>
  http.get(`/classes/${classId}/analytics`)
