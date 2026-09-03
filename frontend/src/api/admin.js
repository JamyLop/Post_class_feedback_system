import http from './index'

export const getAdminStats = () => http.get('/admin/stats')

export const listInviteCodes = (role = '') =>
  http.get('/admin/invite-codes', { params: { role } })
export const createInviteCode = (data) => http.post('/admin/invite-codes', data)
export const disableInviteCode = (id) => http.post(`/admin/invite-codes/${id}/disable`)

export const deleteUser = (id) => http.delete(`/admin/users/${id}`)
export const listGuardianLinks = () => http.get('/admin/guardian-links')
export const createGuardianLink = (data) => http.post('/admin/guardian-links', data)
export const deleteGuardianLink = (id) => http.delete(`/admin/guardian-links/${id}`)
export const listConsultantLinks = () => http.get('/admin/consultant-links')
export const createConsultantLink = (data) => http.post('/admin/consultant-links', data)
export const deleteConsultantLink = (id) => http.delete(`/admin/consultant-links/${id}`)
