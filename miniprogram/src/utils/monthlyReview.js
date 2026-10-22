// 历史自由文本放入总结，编辑时补充问题和计划，原文不会丢失。
export const reviewFields = [
  { key: 'summary', label: '总结', minLength: 50, placeholder: '填写本月表现、进步与完成情况，至少50字' },
  { key: 'problems', label: '问题', minLength: 50, placeholder: '填写存在的问题及具体表现，至少50字' },
  { key: 'plan', label: '计划', placeholder: '填写下月目标与具体改进措施' },
]
export function parseReview(content = '') {
  const match = content.match(/^【总结】\n([\s\S]*?)\n\n【问题】\n([\s\S]*?)\n\n【计划】\n([\s\S]*)$/)
  return match ? { summary: match[1], problems: match[2], plan: match[3] } : { summary: content, problems: '', plan: '' }
}
export function formatReview(values) {
  return reviewFields.map(field => `【${field.label}】\n${values[field.key] || ''}`).join('\n\n')
}
// 最低字数按 Unicode 字符统计，空格和换行不计入，与后端保持一致。
export function reviewWordCount(value = '') {
  return Array.from(value.replace(/\s/gu, '')).length
}
export function reviewError(content) {
  const values = parseReview(content)
  for (const field of reviewFields) {
    if (!values[field.key].trim()) return `请填写${field.label}`
    if (field.minLength && reviewWordCount(values[field.key]) < field.minLength) return `${field.label}至少填写${field.minLength}字（不含空白）`
  }
  return ''
}
export function completeReview(content) {
  return !reviewError(content)
}
