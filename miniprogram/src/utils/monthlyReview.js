// 历史自由文本放入总结，编辑时补充问题和计划，原文不会丢失。
export const reviewFields = [
  { key: 'summary', label: '总结', placeholder: '填写本月表现、进步与完成情况' },
  { key: 'problems', label: '问题', placeholder: '填写存在的问题；无问题可填写“暂无”' },
  { key: 'plan', label: '计划', placeholder: '填写下月目标与具体改进措施' },
]
export function parseReview(content = '') {
  const match = content.match(/^【总结】\n([\s\S]*?)\n\n【问题】\n([\s\S]*?)\n\n【计划】\n([\s\S]*)$/)
  return match ? { summary: match[1], problems: match[2], plan: match[3] } : { summary: content, problems: '', plan: '' }
}
export function formatReview(values) {
  return reviewFields.map(field => `【${field.label}】\n${values[field.key] || ''}`).join('\n\n')
}
export function completeReview(content) {
  const values = parseReview(content)
  return reviewFields.every(field => values[field.key].trim())
}
