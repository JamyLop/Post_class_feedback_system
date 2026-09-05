export const ROLE_HOMES = {
  admin: '/admin/case-supervision',
  deyu_director: '/deyu/cases',
  teacher: '/teacher/student-cases',
  subject_teacher: '/subject/cases',
  consultant: '/consultant/cases',
  student: '/student/assignments',
  parent: '/parent/children',
}

export function homeForRole(role) {
  return ROLE_HOMES[role] || '/login'
}
