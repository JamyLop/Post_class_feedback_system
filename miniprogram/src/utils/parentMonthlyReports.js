import { parseReview, reviewFields } from './monthlyReview.js'

export function formatMonth(label = '') {
  const match = /^(\d{4})-(\d{2})$/.exec(label)
  return match ? `${match[1]}年${Number(match[2])}月` : label
}

// 主报告和班主任评价保存的是同一份德育正文，只展示一次。
export function monthlySubjects(reports = [], { publishedOnly = true, includeEmpty = false } = {}) {
  const subjects = new Map()
  function add(subject, entry) {
    if (!includeEmpty && !entry.content?.trim()) return
    if (!subjects.has(subject)) subjects.set(subject, { subject, entries: [] })
    subjects.get(subject).entries.push(entry)
  }
  for (const report of reports) {
    // 家长默认只看已发布内容；管理员阅读页保留待发布和空白科目。
    if (publishedOnly && report.status !== 'published') continue
    const evaluations = report.evaluations || []
    const head = evaluations.find(item => item.teacher_role === 'head_teacher')
    add('德育', {
      key: `${report.id}-moral`, content: report.final_content?.trim() ? report.final_content : head?.content,
      teacher: head?.teacher_name || '班主任', className: report.class_name || '',
    })
    for (const item of evaluations) {
      if (item.teacher_role === 'head_teacher') continue
      // 一个教师可能同时负责多科，各科入口均保留这份联合评定。
      const names = [...new Set((item.subject || '综合').split('、').map(name => name.trim()).filter(Boolean))]
      for (const subject of names) add(subject, {
        key: `${report.id}-${item.id}`, content: item.content,
        teacher: item.teacher_name || '任课老师', className: report.class_name || '',
      })
    }
  }
  return [...subjects.values()]
}

export function monthlyGroups(reports = []) {
  const months = new Map()
  for (const report of reports) {
    if (report.status !== 'published') continue
    if (!months.has(report.month_label)) months.set(report.month_label, [])
    months.get(report.month_label).push(report)
  }
  return [...months.entries()].sort(([a], [b]) => b.localeCompare(a)).map(([month, rows]) => ({
    month, label: formatMonth(month), subjectCount: monthlySubjects(rows).length,
  }))
}

export function reviewSections(content = '') {
  const values = parseReview(content)
  // 自由文本保持原样，避免把历史正文误标成结构化的“总结”。
  if (!values.problems && !values.plan) return [{ key: 'content', label: '评定内容', content }]
  return reviewFields.map(field => ({ ...field, content: values[field.key] || '暂无内容' }))
}
