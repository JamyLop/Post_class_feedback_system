export const ROLE_HOMES = {
  admin: '/admin/dashboard',
  teacher: '/teacher/assignments',
  student: '/student/assignments',
}

export function homeForRole(role) {
  return ROLE_HOMES[role] || '/login'
}
