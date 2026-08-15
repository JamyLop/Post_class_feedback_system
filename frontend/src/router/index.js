import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { homeForRole } from './roleHome'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  { path: '/register', component: () => import('../views/Register.vue') },
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { roles: ['admin'] },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'users', component: () => import('../views/admin/Users.vue') },
      { path: 'invite-codes', component: () => import('../views/admin/InviteCodes.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/TeacherLayout.vue'),
    meta: { roles: ['admin', 'teacher'] },
    children: [
      { path: '', redirect: '/teacher/assignments' },
      { path: 'teacher/classes', component: () => import('../views/teacher/Classes.vue') },
      { path: 'teacher/classes/:id/students', component: () => import('../views/teacher/ClassStudents.vue') },
      { path: 'teacher/assignments', component: () => import('../views/teacher/Assignments.vue') },
      { path: 'teacher/assignments/new', component: () => import('../views/teacher/AssignmentEdit.vue') },
      { path: 'teacher/assignments/:id', component: () => import('../views/teacher/AssignmentDetail.vue') },
      { path: 'teacher/questions', component: () => import('../views/teacher/Questions.vue') },
      { path: 'teacher/reviews', component: () => import('../views/teacher/Review.vue') },
      { path: 'teacher/reviews/:submissionId', component: () => import('../views/teacher/ReviewSubmission.vue') },
      { path: 'teacher/assignments/:id/submissions', component: () => import('../views/teacher/AssignmentSubmissions.vue') },
      { path: 'teacher/assignments/:id/analysis', component: () => import('../views/teacher/AssignmentAnalysis.vue') },
      { path: 'teacher/student-analytics', component: () => import('../views/teacher/StudentAnalytics.vue') },
      { path: 'teacher/class-analytics', component: () => import('../views/teacher/ClassAnalytics.vue') },
      { path: 'teacher/feedback', component: () => import('../views/teacher/Feedback.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/StudentLayout.vue'),
    meta: { roles: ['student'] },
    children: [
      { path: 'student/assignments', component: () => import('../views/student/Assignments.vue') },
      { path: 'student/assignments/:id', component: () => import('../views/student/AssignmentDetail.vue') },
      { path: 'student/submissions/:id', component: () => import('../views/student/SubmissionResult.vue') },
      { path: 'student/my-analytics', component: () => import('../views/student/MyAnalytics.vue') },
      { path: 'student/my-feedback', component: () => import('../views/student/MyFeedback.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const publicPaths = ['/login', '/register']
  if (!publicPaths.includes(to.path) && !auth.isLoggedIn) {
    return '/login'
  }
  const role = auth.role
  if (to.meta.roles) {
    // 有 token 但角色数据陈旧/无效：登出并回登录页，避免守卫死循环白屏
    if (!['admin', 'teacher', 'student'].includes(role)) {
      auth.logout()
      return '/login'
    }
    if (!to.meta.roles.includes(role)) {
      return homeForRole(role)
    }
  }
  return true
})

export default router
