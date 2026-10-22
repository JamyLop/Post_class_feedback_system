import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '../../stores/auth'
import { getMonthlyReport } from '../../api/monthlyReports'
import { monthlySubjects } from '../../utils/parentMonthlyReports'

export function useAdminMonthlyReport() {
  const auth = useAuthStore()
  const report = ref(null)
  const loading = ref(true)
  const error = ref('')
  const reportId = ref(0)
  const subject = ref('')
  const readOnly = ref(false)
  const subjects = computed(() => monthlySubjects(report.value ? [report.value] : [], { publishedOnly: false, includeEmpty: true }))
  const status = computed(() => ({ generating: '待填写', generated: '待发布', published: '已发布', failed: '待补充' }[report.value?.status] || ''))

  onLoad(options => {
    reportId.value = Number(options.id)
    readOnly.value = options.readonly === '1'
    subject.value = options.subject || ''
    // 微信 onLoad 可能保留中文 URL 编码，H5 可能已经解码。
    try { subject.value = decodeURIComponent(subject.value) } catch (_) {}
  })
  async function load() {
    if (!auth.isLoggedIn) { uni.reLaunch({ url: '/pages/login/index' }); return }
    if (auth.role !== 'admin') { uni.reLaunch({ url: '/pages/index/index' }); return }
    loading.value = true
    error.value = ''
    report.value = null
    try {
      if (!Number.isSafeInteger(reportId.value) || reportId.value <= 0) throw new Error('页面参数有误，请返回评定列表重新选择')
      report.value = await getMonthlyReport(reportId.value)
    } catch (e) {
      error.value = e.message || '月度评定加载失败，请重试'
    } finally { loading.value = false }
  }
  onShow(load)
  return { report, loading, error, reportId, subject, readOnly, subjects, status, load }
}
