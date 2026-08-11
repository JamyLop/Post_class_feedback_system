import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../layouts/TeacherLayout.vue'),
    meta: { role: 'teacher' },
    children: [
      { path: '', redirect: '/teacher/assignments' },
      { path: 'teacher/classes', component: () => import('../views/teacher/Classes.vue') },
      { path: 'teacher/classes/:id/students', component: () => import('../views/teacher/ClassStudents.vue') },
      { path: 'teacher/assignments', component: () => import('../views/teacher/Assignments.vue') },
      { path: 'teacher/assignments/new', component: () => import('../views/teacher/AssignmentEdit.vue') },
      { path: 'teacher/assignments/:id', component: () => import('../views/teacher/AssignmentDetail.vue') },
      { path: 'teacher/questions', component: () => import('../views/teacher/Questions.vue') },
      { path: 'teacher/assignments/:id/submissions', component: () => import('../views/teacher/AssignmentSubmissions.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/StudentLayout.vue'),
    meta: { role: 'student' },
    children: [
      { path: 'student/assignments', component: () => import('../views/student/Assignments.vue') },
      { path: 'student/assignments/:id', component: () => import('../views/student/AssignmentDetail.vue') },
      { path: 'student/submissions/:id', component: () => import('../views/student/SubmissionResult.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) {
    return '/login'
  }
  if (to.meta.role && auth.isLoggedIn && to.meta.role !== auth.role) {
    return auth.role === 'teacher' ? '/teacher/assignments' : '/student/assignments'
  }
  return true
})

export default router
