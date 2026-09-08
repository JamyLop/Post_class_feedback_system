// 菜单仅表达已实现的入口；最终的数据与写操作权限仍由后端校验。
export const ROLE_LABELS = { parent: '家长', student: '学生', teacher: '班主任', deyu_director: '德育主任', admin: '校长', consultant: '咨询老师', subject_teacher: '任课老师' }
export const ENTRIES = [
  { roles: ['teacher', 'deyu_director', 'admin'], title: '待办与进展', desc: '查看档案状态与待处理事项', route: '/subTeacher/todo/index', group: '档案工作' },
  { roles: ['teacher', 'deyu_director', 'admin', 'subject_teacher'], title: '学生档案', desc: '查阅学科方案、任务与过程记录', route: '/subTeacher/caseList/index', group: '档案工作' },
  { roles: ['deyu_director'], title: '方案审查', desc: '审查通过或退回班主任整改', route: '/subTeacher/deyuReview/index', group: '档案工作' },
  { roles: ['parent'], title: '孩子档案', desc: '查看已发布方案与成长记录', route: '/subParent/children/index', group: '成长档案' },
  { roles: ['student'], title: '我的档案', desc: '查看目标、学科方案与执行进展', route: '/pages/student/myCase/index', group: '成长档案' },
  { roles: ['consultant'], title: '关联学生', desc: '查阅所负责学生的学业档案', route: '/subConsultant/caseList/index', group: '成长档案' },
  { roles: ['student'], title: '学情分析', desc: '查看周测成绩与变化趋势', route: '/pages/student/analytics/index', group: '学习记录' },
  { roles: ['student'], title: '月度评定', desc: '阅读老师发布的月度评定', route: '/pages/student/monthlyReports/index', group: '学习记录' },
  { roles: ['student'], title: '个人信息', desc: '查看学籍与账号基本信息', route: '/pages/student/profile/index', group: '账号信息' },
  { roles: ['teacher', 'admin', 'subject_teacher', 'deyu_director'], title: '周测成绩', desc: '查看成绩、班级汇总与教师评价', route: '/subTeacher/weeklyScores/index', group: '教学管理' },
  { roles: ['consultant'], title: '学生周测', desc: '查看所负责学生的周测成绩', route: '/subTeacher/weeklyScores/index', group: '成长档案' },
  { roles: ['teacher', 'admin'], title: '月度评定', desc: '手动填写、审阅与发布评定', route: '/subTeacher/monthlyReports/index', group: '教学管理' },
  { roles: ['teacher', 'admin', 'deyu_director'], title: '积分周月报', desc: '一键生成并查看班级积分周报、月报', route: '/subTeacher/pointsReports/index', group: '教学管理' },
  { roles: ['teacher', 'admin'], title: '班级管理', desc: '管理班级与学生信息', route: '/subTeacher/classManager/index', group: '教学管理' },
  { roles: ['admin'], title: '系统管理', desc: '查看统计、管理用户与邀请码', route: '/subTeacher/adminStats/index', group: '系统管理' },
]
export function entriesForRole(role) { return ENTRIES.filter(entry => entry.roles.includes(role)) }
export function groupsForRole(role) {
  return [...new Set(entriesForRole(role).map(entry => entry.group))].map(title => ({ title, entries: entriesForRole(role).filter(entry => entry.group === title) }))
}
