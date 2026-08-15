import http from './index'

export const getAdminStats = () => http.get('/admin/stats')

export const listInviteCodes = (role = '') =>
  http.get('/admin/invite-codes', { params: { role } })
export const createInviteCode = (data) => http.post('/admin/invite-codes', data)
export const disableInviteCode = (id) => http.post(`/admin/invite-codes/${id}/disable`)

export const deleteUser = (id) => http.delete(`/admin/users/${id}`)
