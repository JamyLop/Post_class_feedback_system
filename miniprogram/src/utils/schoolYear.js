export function currentSchoolYear(now = new Date()) {
  const year = now.getFullYear()
  // 学年以8月为界：1—7月仍属于上一学年，避免跨年后继续使用写死的默认值。
  const startYear = now.getMonth() >= 7 ? year : year - 1
  return `${startYear}-${startYear + 1}`
}
