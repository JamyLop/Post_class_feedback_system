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
      { path: '', redirect: '/admin/case-supervision' },
      { path: 'case-supervision', component: () => import('../views/admin/CaseSupervision.vue') },
      { path: 'cases/:id', component: () => import('../views/teacher/StudentCaseDetail.vue') },
      { path: 'dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'users', component: () => import('../views/admin/Users.vue') },
      { path: 'invite-codes', component: () => import('../views/admin/InviteCodes.vue') },
      { path: 'guardian-links', redirect: '/admin/consultant-links' },
      { path: 'consultant-links', component: () => import('../views/admin/ConsultantLinks.vue') },
      { path: 'subject-links', component: () => import('../views/admin/ClassTeacherLinks.vue') },
    ],
  },
  {
    path: '/deyu',
    component: () => import('../layouts/DeyuLayout.vue'),
    meta: { roles: ['deyu_director'] },
    children: [
      { path: '', redirect: '/deyu/cases' },
      { path: 'cases', component: () => import('../views/deyu/DeyuCases.vue') },
      { path: 'cases/:id', component: () => import('../views/teacher/StudentCaseDetail.vue') },
    ],
  },
  {
    path: '/parent',
    component: () => import('../layouts/ParentLayout.vue'),
    meta: { roles: ['parent'] },
    children: [
      { path: '', redirect: '/parent/children' },
      { path: 'children', component: () => import('../views/parent/ChildrenCases.vue') },
      { path: 'children/:id', component: () => import('../views/teacher/StudentCaseDetail.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/TeacherLayout.vue'),
    meta: { roles: ['admin', 'teacher', 'deyu_director'] },
    children: [
      { path: '', redirect: '/teacher/student-cases' },
      { path: 'teacher/student-cases', component: () => import('../views/teacher/StudentCases.vue') },
      { path: 'teacher/student-cases/:id', component: () => import('../views/teacher/StudentCaseDetail.vue') },
      { path: 'teacher/classes', component: () => import('../views/teacher/Classes.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/classes/:id/students', component: () => import('../views/teacher/ClassStudents.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/assignments', component: () => import('../views/teacher/Assignments.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/assignments/new', component: () => import('../views/teacher/AssignmentEdit.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/assignments/:id', component: () => import('../views/teacher/AssignmentDetail.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/questions', component: () => import('../views/teacher/Questions.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/reviews', component: () => import('../views/teacher/Review.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/reviews/:submissionId', component: () => import('../views/teacher/ReviewSubmission.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/assignments/:id/submissions', component: () => import('../views/teacher/AssignmentSubmissions.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/assignments/:id/analysis', component: () => import('../views/teacher/AssignmentAnalysis.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/student-analytics', component: () => import('../views/teacher/StudentAnalytics.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/class-analytics', component: () => import('../views/teacher/ClassAnalytics.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/feedback', component: () => import('../views/teacher/Feedback.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/weekly-scores', component: () => import('../views/teacher/WeeklyScores.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/monthly-reports', component: () => import('../views/teacher/MonthlyReports.vue'), meta: { roles: ['admin', 'teacher'] } },
      { path: 'teacher/task-reminders', component: () => import('../views/teacher/TaskReminders.vue'), meta: { roles: ['teacher'] } },
      { path: 'teacher/points-reports', component: () => import('../views/teacher/PointsReports.vue'), meta: { roles: ['admin', 'teacher'] } },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/SubjectLayout.vue'),
    meta: { roles: ['subject_teacher'] },
    children: [
      { path: '', redirect: '/subject/cases' },
      { path: 'subject/cases', component: () => import('../views/subject/SubjectCases.vue') },
      { path: 'subject/cases/:id', component: () => import('../views/teacher/StudentCaseDetail.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/ConsultantLayout.vue'),
    meta: { roles: ['consultant'] },
    children: [
      { path: '', redirect: '/consultant/cases' },
      { path: 'consultant/cases', component: () => import('../views/consultant/ConsultantCases.vue') },
      { path: 'consultant/cases/:id', component: () => import('../views/teacher/StudentCaseDetail.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/StudentLayout.vue'),
    meta: { roles: ['student'] },
    children: [
      { path: '', redirect: '/student/assignments' },
      { path: 'student/assignments', component: () => import('../views/student/Assignments.vue') },
      { path: 'student/assignments/:id', component: () => import('../views/student/AssignmentDetail.vue') },
      { path: 'student/submissions/:id', component: () => import('../views/student/SubmissionResult.vue') },
      { path: 'student/my-analytics', component: () => import('../views/student/MyAnalytics.vue') },
      { path: 'student/my-feedback', component: () => import('../views/student/MyFeedback.vue') },
      { path: 'student/my-weekly-scores', component: () => import('../views/student/MyWeeklyScores.vue') },
      { path: 'student/my-monthly-reports', component: () => import('../views/student/MyMonthlyReports.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 档案列表与详情的内容高度差异很大，切换页面时必须从顶部开始阅读。
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0, left: 0 }
  },
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
    if (!['admin', 'deyu_director', 'teacher', 'subject_teacher', 'student', 'parent', 'consultant'].includes(role)) {
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
