import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { listMonthlyReports } from '../../api/monthlyReports'

export function useMonthlyReports() {
  const auth = useAuthStore()
  const loading = ref(true)
  const error = ref('')
  const reports = ref([])
  const studentId = ref(0)
  const month = ref('')
  const subject = ref('')

  onLoad(options => {
    studentId.value = Number(options.studentId)
    month.value = options.month || ''
    subject.value = options.subject || ''
    // 微信 onLoad 保留 URL 编码，H5 通常已解码；统一还原后再按科目匹配正文。
    try { subject.value = decodeURIComponent(subject.value) } catch (_) {
      // 保留损坏的参数供空状态处理，避免 URIError 中断整个页面。
    }
  })
  async function load() {
    if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return }
    if (!['parent', 'student'].includes(auth.role)) { uni.reLaunch({ url: '/pages/index/index' }); return }
    reports.value = []
    error.value = ''
    loading.value = true
    try {
      if (!Number.isSafeInteger(studentId.value) || studentId.value <= 0 || !/^\d{4}-(0[1-9]|1[0-2])$/.test(month.value)) {
        throw new Error('页面参数有误，请返回月份列表重新选择')
      }
      const rows = []
      for (let offset = 0; ; offset += 200) {
        const batch = await listMonthlyReports({ student_id: studentId.value, month_label: month.value, status: 'published', limit: 200, offset })
        rows.push(...batch)
        if (batch.length < 200) break
      }
      reports.value = rows
    } catch (e) {
      error.value = e.message || '月度评定加载失败，请重试'
    } finally { loading.value = false }
  }
  onShow(load)
  return { loading, error, reports, studentId, month, subject, load }
}
