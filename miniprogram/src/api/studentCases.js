import { http, getApiBase } from '../utils/request'

// ---- 班级 ----
export const listClasses = () => http.get('/classes')
export const listClassStudents = (classId) => http.get(`/classes/${classId}/students`)

// ---- 一生一案：查询 ----
export const listStudentCases = (params = {}) => http.get('/student-cases', params)
export const listCaseCycles = () => http.get('/student-cases/cycles')
export const createCaseCycle = (data) => http.post('/student-cases/cycles', data)
export const addStudentsToClass = (classId, studentIds) => http.post(`/classes/${classId}/students`, { student_ids: studentIds })
export const getStudentCase = (id) => http.get(`/student-cases/${id}`)
export const getFamilyCases = () => http.get('/student-cases/children')
export const getCaseProgress = (params = {}) => http.get('/student-cases/progress', params)
export const getCaseVersions = (caseId) => http.get(`/student-cases/${caseId}/versions`)
export const getMyChildren = () => http.get('/auth/me/children')
export const getMyCase = () => http.get('/student-cases/my-case')

// ---- 一生一案：写操作（班主任） ----
export const createStudentCase = (data) => http.post('/student-cases', data)
export const updateStudentCase = (caseId, data) => http.patch(`/student-cases/${caseId}`, data)
export const transitionCase = (caseId, data) => http.post(`/student-cases/${caseId}/transition`, data)
export const upsertSubjectPlan = (caseId, subject, data) => http.put(`/student-cases/${caseId}/subject-plans/${encodeURIComponent(subject)}`, data)
export const createGoal = (caseId, data) => http.post(`/student-cases/${caseId}/goals`, data)
export const createTask = (caseId, data) => http.post(`/student-cases/${caseId}/tasks`, data)
export const updateTask = (caseId, taskId, data) => http.put(`/student-cases/${caseId}/tasks/${taskId}`, data)
export const requestTaskChange = (caseId, taskId, data) => http.post(`/student-cases/${caseId}/tasks/${taskId}/change-request`, data)
export const listTaskChangeRequests = (params = {}) => http.get('/student-cases/tasks/change-requests', params)
export const decideTaskChange = (reviewId, data) => http.post(`/student-cases/reviews/${reviewId}/decide`, data)
export const checkinCaseTask = (taskId, data) => http.post(`/student-cases/tasks/${taskId}/checkins`, data)

// 打卡照片上传：multipart field `file`，仅班主任；后端限制 10MB 内 PNG/JPEG/GIF/WebP
// uni.request 不能发 multipart，此处用 uni.uploadFile 直调，语义与 Web 端 uploadCheckinAttachment 一致
export function uploadCheckinAttachment(checkinId, filePath, opts = {}) {
  const token = uni.getStorageSync('token') || ''
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${getApiBase()}/student-cases/task-checkins/${checkinId}/attachments`,
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success(res) {
        if (res.statusCode === 401) {
          uni.showToast({ title: '登录已过期', icon: 'none' })
          reject({ status: 401, message: '未登录' })
          return
        }
        let payload = null
        try {
          payload = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        } catch (_) {}
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(payload)
        } else {
          const detail = payload?.detail
          const msg = typeof detail === 'string' ? detail : `上传失败(${res.statusCode})`
          if (opts.showError !== false) uni.showToast({ title: msg.slice(0, 40), icon: 'none' })
          reject({ status: res.statusCode, message: msg, data: payload })
        }
      },
      fail(err) {
        const msg = err.errMsg || '网络异常'
        if (opts.showError !== false) uni.showToast({ title: msg.slice(0, 40), icon: 'none' })
        reject({ status: 0, message: msg })
      },
    })
  })
}
export const createCaseReview = (caseId, data) => http.post(`/student-cases/${caseId}/reviews`, data)

// ---- 德育主任审查 ----
export const deyuReview = (caseId, data) => http.post(`/student-cases/${caseId}/deyu-review`, data)

// ---- 学科建议（任课老师） ----
export const listSubjectSuggestions = (caseId) => http.get(`/student-cases/${caseId}/subject-suggestions`)
export const createSubjectSuggestion = (caseId, data) => http.post(`/student-cases/${caseId}/subject-suggestions`, data)

// ---- 管理员 ----
export const getAdminStats = () => http.get('/admin/stats')
export const listInviteCodes = (params = {}) => http.get('/admin/invite-codes', params)
export const createInviteCode = (data) => http.post('/admin/invite-codes', data)
export const disableInviteCode = (id) => http.post(`/admin/invite-codes/${id}/disable`)
export const listGuardianLinks = () => http.get('/admin/guardian-links')
export const createGuardianLink = (data) => http.post('/admin/guardian-links', data)
export const deleteGuardianLink = (id) => http.del(`/admin/guardian-links/${id}`)
export const adminDeleteUser = (id) => http.del(`/admin/users/${id}`)

// ---- 用户管理（admin+teacher） ----
export const listUsers = (params = {}) => http.get('/users', params)
export const getUser = (id) => http.get(`/users/${id}`)
export const createUser = (data) => http.post('/users', data)
export const updateUser = (id, data) => http.put(`/users/${id}`, data)
