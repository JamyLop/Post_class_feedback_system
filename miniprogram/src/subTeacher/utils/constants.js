export const CASE_STATUS_LABELS = {
  draft: '草稿',
  pending_confirmation: '待德育审查',
  revision_required: '待班主任整改',
  executing: '执行中',
  pending_review: '待复盘',
  adjusted: '已调整',
  archived: '已归档',
}

export const ROLE_LABELS = {
  parent: '家长',
  student: '学生',
  teacher: '班主任',
  deyu_director: '德育主任',
  admin: '校长',
}

// 班级管理入口与学生名册必须共用同一角色范围，避免能进入班级列表却被子页面退回首页。
export const CLASS_MANAGEMENT_ROLES = Object.freeze(['teacher', 'admin', 'deyu_director'])
